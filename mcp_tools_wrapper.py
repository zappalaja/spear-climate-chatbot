import sys
import os
import asyncio
import json
from datetime import datetime
from plotting_tool import plot_climate_data
from response_size_estimator import is_query_too_large, suggest_alternatives, format_size_warning

# MCP Client imports
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# Check if we should use HTTP or stdio transport
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
USE_HTTP_TRANSPORT = MCP_SERVER_URL is not None

if USE_HTTP_TRANSPORT:
    print(f"[MCP CONFIG] Using HTTP SSE transport to: {MCP_SERVER_URL}")
    try:
        from mcp.client.sse import sse_client
        print("[MCP CONFIG] SSE client imported successfully")
    except ImportError:
        print("[MCP CONFIG] WARNING: SSE client not available, falling back to httpx")
        import httpx
else:
    # MCP Server configuration - using stdio transport to spear-mcp (local development)
    print("[MCP CONFIG] Using stdio transport (local development)")
    MCP_SERVER_PARAMS = StdioServerParameters(
        command="uv",
        args=["--directory", "/home/zappalaj/spear-mcp-test", "run", "spear-mcp"]
    )

# Define available tools with their metadata
AVAILABLE_TOOLS = [
    {
        "name": "create_plot",
        "description": "Create and display a matplotlib plot",
        "function": plot_climate_data
    },
    {
        "name": "browse_spear_directory",
        "description": "Browse SPEAR directory structure step by step",
        "mcp_tool": True
    },
    {
        "name": "search_spear_variables",
        "description": "Search for variables across SPEAR datasets",
        "mcp_tool": True
    },
    {
        "name": "get_s3_file_metadata_only",
        "description": "Get metadata of a SPEAR NetCDF file without loading data",
        "mcp_tool": True
    },
    {
        "name": "query_netcdf_data",
        "description": "Query NetCDF data with spatial/temporal subsetting",
        "mcp_tool": True
    }
]


# ============================================================================
# RESPONSE SIZE CHECKING FUNCTIONS
# ============================================================================

def parse_time_range(start_date, end_date, frequency="Amon"):
    """
    Calculate number of time points from date range.

    Args:
        start_date: Start date string (YYYY-MM or YYYY-MM-DD)
        end_date: End date string (YYYY-MM or YYYY-MM-DD)
        frequency: Data frequency (default: Amon for monthly)

    Returns:
        Number of time points
    """
    if not start_date or not end_date:
        # If no dates provided, assume worst case (full historical + SSP5-85)
        # Historical: 1850-2014 (165 years)
        # SSP5-85: 2015-2100 (86 years)
        # Total: 251 years
        if frequency == "Amon":
            return 251 * 12  # ~3000 monthly time points
        elif frequency == "day":
            return 251 * 365  # ~91,000 daily time points
        else:
            return 251 * 12  # Default to monthly

    # Parse year and month from dates
    from datetime import datetime

    try:
        # Handle YYYY-MM format
        if len(start_date) == 7:  # YYYY-MM
            start = datetime.strptime(start_date, "%Y-%m")
            end = datetime.strptime(end_date, "%Y-%m")
        else:  # YYYY-MM-DD
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

        # Calculate time difference
        years = (end.year - start.year)
        months = (end.month - start.month)
        total_months = years * 12 + months + 1  # +1 to include end month

        # Convert to time points based on frequency
        if frequency == "Amon":
            return total_months
        elif frequency == "day":
            return total_months * 30  # Approximate days
        else:
            return total_months
    except:
        # If parsing fails, return conservative estimate
        return 1000


def estimate_spatial_points(lat_range, lon_range):
    """
    Estimate number of grid points from lat/lon ranges.

    Args:
        lat_range: [min_lat, max_lat] or None
        lon_range: [min_lon, max_lon] or None

    Returns:
        (lat_points, lon_points)
    """
    # SPEAR_MED resolution is approximately 1 degree
    SPEAR_LAT_RESOLUTION = 1.0  # degrees
    SPEAR_LON_RESOLUTION = 1.0  # degrees

    if lat_range is None or lon_range is None:
        # Global grid
        return 180, 360

    # Calculate points from ranges
    lat_points = int(abs(lat_range[1] - lat_range[0]) / SPEAR_LAT_RESOLUTION)
    lon_points = int(abs(lon_range[1] - lon_range[0]) / SPEAR_LON_RESOLUTION)

    # Ensure at least 1 point
    lat_points = max(1, lat_points)
    lon_points = max(1, lon_points)

    return lat_points, lon_points


def check_query_size_before_execution(tool_input):
    """
    Check if a query_netcdf_data query would be too large.
    Returns None if query is OK, or error response if too large.

    Args:
        tool_input: Dictionary with query parameters

    Returns:
        None if OK, or dict with error/warning if too large
    """
    # Extract parameters from tool input
    start_date = tool_input.get("start_date")
    end_date = tool_input.get("end_date")
    lat_range = tool_input.get("lat_range")
    lon_range = tool_input.get("lon_range")
    frequency = tool_input.get("frequency", "Amon")
    variable = tool_input.get("variable", "unknown")
    scenario = tool_input.get("scenario", "scenarioSSP5-85")
    ensemble = tool_input.get("ensemble_member", "r15i1p1f1")

    # ========================================================================
    # VALIDATE AND AUTO-CONVERT LAT/LON RANGES
    # ========================================================================
    # SPEAR grid ranges:
    # - Latitude: -89.5 to 89.5 (valid range)
    # - Longitude: 0.3125 to 359.6875 (0-360 format, NOT -180 to 180!)

    conversion_notes = []

    # Validate and fix latitude
    if lat_range is not None:
        min_lat, max_lat = lat_range
        if min_lat < -90 or max_lat > 90:
            return {
                "status": "error",
                "error": "Invalid latitude range",
                "warning_message": f"**Invalid Latitude Range**\n\nLatitude must be between -90 and 90 degrees.\nYou provided: {lat_range}"
            }
        if min_lat >= max_lat:
            return {
                "status": "error",
                "error": "Invalid latitude range",
                "warning_message": f"**Invalid Latitude Range**\n\nmin_lat must be less than max_lat.\nYou provided: {lat_range}"
            }

    # Auto-convert longitude from -180/180 to 0-360 format
    if lon_range is not None:
        min_lon, max_lon = lon_range
        original_range = lon_range.copy() if isinstance(lon_range, list) else list(lon_range)

        # Convert negative longitudes to 0-360
        if min_lon < 0:
            min_lon = min_lon + 360
            conversion_notes.append(f"Converted min_lon: {original_range[0]}° → {min_lon}°")
        if max_lon < 0:
            max_lon = max_lon + 360
            conversion_notes.append(f"Converted max_lon: {original_range[1]}° → {max_lon}°")

        # Update tool_input with converted values
        tool_input["lon_range"] = [min_lon, max_lon]

        # Validate final range
        if min_lon > 360 or max_lon > 360:
            return {
                "status": "error",
                "error": "Invalid longitude range",
                "warning_message": f"**Invalid Longitude Range**\n\nLongitude must be between 0 and 360 degrees.\nConverted range: [{min_lon}, {max_lon}]"
            }

    # Log conversions for debugging
    if conversion_notes:
        print(f"[COORDINATE CONVERSION] {'; '.join(conversion_notes)}")  # DEBUG

    # Calculate dimensions
    time_points = parse_time_range(start_date, end_date, frequency)
    lat_points, lon_points = estimate_spatial_points(lat_range, lon_range)

    # Check if too large (use function from response_size_estimator)
    is_too_large, estimated_tokens, message = is_query_too_large(
        time_points,
        lat_points,
        lon_points,
        current_conversation_tokens=15000  # Conservative estimate
    )

    if is_too_large:
        # Generate suggestions
        suggestions = suggest_alternatives(
            time_points,
            lat_points,
            lon_points,
            variable,
            scenario,
            ensemble
        )

        # Format warning message
        warning = format_size_warning(estimated_tokens, suggestions)

        # Return as error response (prevents tool execution)
        return {
            "status": "error",
            "error": "Query too large - response would exceed token limits",
            "warning_message": warning,
            "estimated_tokens": estimated_tokens,
            "data_shape": {
                "time_points": time_points,
                "lat_points": lat_points,
                "lon_points": lon_points,
                "total_data_points": time_points * lat_points * lon_points
            },
            "suggestions": suggestions
        }

    # Query size is acceptable - return None to proceed with execution
    return None


async def call_mcp_server_http(tool_name, tool_input):
    """Call the MCP server using FastMCP HTTP protocol"""
    import traceback
    import httpx

    try:
        mcp_url = MCP_SERVER_URL + "/mcp"
        print(f"[MCP] Connecting to FastMCP: {mcp_url}")
        print(f"[MCP] Tool: {tool_name}, Input: {tool_input}")

        # Increase timeout for S3 data fetching operations
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: Initialize session
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "spear-chatbot", "version": "1.0"}
                }
            }

            response = await client.post(
                mcp_url,
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            response.raise_for_status()

            # Extract session ID from headers
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                raise Exception("No session ID received from server")

            print(f"[MCP] Session initialized: {session_id}")

            # Step 2: Send initialized notification
            init_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }

            await client.post(
                mcp_url,
                json=init_notification,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": session_id
                }
            )

            print(f"[MCP] Sent initialized notification")

            # Step 3: Call the tool
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_input
                }
            }

            response = await client.post(
                mcp_url,
                json=tool_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": session_id
                }
            )
            response.raise_for_status()

            # Parse SSE response
            response_text = response.text
            # SSE format: "event: message\ndata: {...}\n\n"
            if "data: " in response_text:
                json_data = response_text.split("data: ")[1].strip()
                result = json.loads(json_data)

                if "error" in result:
                    return {
                        "status": "error",
                        "error": f"MCP server error: {result['error']}"
                    }

                # Extract result from MCP response
                if "result" in result:
                    mcp_result = result["result"]
                    # Check if content is wrapped
                    if isinstance(mcp_result, dict) and "content" in mcp_result:
                        content_list = mcp_result["content"]
                        if len(content_list) > 0:
                            content = content_list[0]
                            if "text" in content:
                                data = content["text"]
                                try:
                                    data = json.loads(data)
                                except:
                                    pass
                            else:
                                data = content
                        else:
                            data = mcp_result
                    else:
                        data = mcp_result

                    return {
                        "status": "ok",
                        "tool": tool_name,
                        "data": data
                    }

            return {
                "status": "error",
                "error": f"Unexpected response format: {response_text}"
            }

    except Exception as e:
        import sys
        error_trace = traceback.format_exc()
        sys.stderr.write(f"[MCP ERROR] {error_trace}\n")
        sys.stderr.flush()
        return {
            "status": "error",
            "error": f"Failed to connect to MCP server: {str(e)}",
            "traceback": error_trace
        }


async def call_mcp_server_stdio(tool_name, tool_input):
    """Call the MCP server using stdio transport"""
    try:
        async with stdio_client(MCP_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, tool_input)

                # Extract content from result
                if result.content:
                    # Handle different content types
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        data = content.text
                        # Try to parse as JSON if possible
                        try:
                            data = json.loads(data)
                        except json.JSONDecodeError:
                            pass
                    else:
                        data = str(content)
                else:
                    data = "No content returned"

                return {
                    "status": "ok",
                    "tool": tool_name,
                    "data": data
                }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to connect to MCP server via stdio: {str(e)}"
        }


async def call_mcp_server(tool_name, tool_input):
    """Call the MCP server using configured transport (HTTP or stdio)"""
    if USE_HTTP_TRANSPORT:
        return await call_mcp_server_http(tool_name, tool_input)
    else:
        return await call_mcp_server_stdio(tool_name, tool_input)


async def query_mcp_tool_async(tool_name, tool_input):
    """Execute a SPEAR tool via MCP server or locally."""
    try:
        import inspect

        # Find the tool
        tool_config = None
        for tool in AVAILABLE_TOOLS:
            if tool["name"] == tool_name:
                tool_config = tool
                break

        if tool_config is None:
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}"
            }

        # Check if this is an MCP tool
        if tool_config.get("mcp_tool", False):
            # Call MCP server
            return await call_mcp_server(tool_name, tool_input)

        # For local tools, get the function
        tool_func = tool_config.get("function")
        if tool_func is None:
            return {
                "status": "error", 
                "error": f"No function defined for tool: {tool_name}"
            }

        # ========================================================================
        # RESPONSE SIZE CHECKING (BEFORE TOOL EXECUTION)
        # ========================================================================
        # For query_netcdf_data, check if response would be too large
        if tool_name == "query_netcdf_data":
            print(f"[SIZE CHECK] Checking query size for: {tool_input}")  # DEBUG
            size_check_result = check_query_size_before_execution(tool_input)
            if size_check_result is not None:
                # Query is too large - return warning instead of executing
                print(f"[SIZE CHECK] Query TOO LARGE - blocking execution")  # DEBUG
                return size_check_result
            print(f"[SIZE CHECK] Query size OK - proceeding with execution")  # DEBUG

        # Execute the tool (handle both async and sync functions)
        if inspect.iscoroutinefunction(tool_func):
            result = await tool_func(**tool_input)
        else:
            result = tool_func(**tool_input)

        # Convert result to JSON-serializable format
        if isinstance(result, dict):
            result_data = result
        else:
            result_data = result.to_dict() if hasattr(result, 'to_dict') else str(result)

        return {
            "status": "ok",
            "tool": tool_name,
            "data": result_data
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": f"Failed to execute tool '{tool_name}': {str(e)}",
            "traceback": traceback.format_exc()
        }


def get_available_tools():
    """Get list of available tools."""
    return {
        "status": "ok",
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in AVAILABLE_TOOLS
        ]
    }


def query_mcp_tool(tool_name, tool_input):
    """Synchronous wrapper for querying an MCP tool."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(query_mcp_tool_async(tool_name, tool_input))
    finally:
        loop.close()

