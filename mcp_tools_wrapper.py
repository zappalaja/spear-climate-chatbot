import sys
import os
import asyncio
import json
from datetime import datetime

# Add the src directory to the system path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from spear_mcp import tools, tools_nc
from plotting_tool import plot_climate_data
from response_size_estimator import is_query_too_large, suggest_alternatives, format_size_warning


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
        "function": tools.browse_spear_directory
    },
    {
        "name": "search_spear_variables",
        "description": "Search for variables across SPEAR datasets",
        "function": tools.search_spear_variables
    },
    {
        "name": "get_s3_file_metadata_only",
        "description": "Get metadata of a SPEAR NetCDF file without loading data",
        "function": tools_nc.get_s3_file_metadata_only
    },
    {
        "name": "query_netcdf_data",
        "description": "Query NetCDF data with spatial/temporal subsetting",
        "function": tools_nc.query_netcdf_data
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


async def query_mcp_tool_async(tool_name, tool_input):
    """Execute a SPEAR tool directly."""
    try:
        import inspect

        # Find the tool
        tool_func = None
        for tool in AVAILABLE_TOOLS:
            if tool["name"] == tool_name:
                tool_func = tool["function"]
                break

        if tool_func is None:
            return {
                "status": "error",
                "error": f"Unknown tool: {tool_name}"
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

