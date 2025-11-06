"""
Claude API Tool Definitions for SPEAR MCP Tools and Plotting
"""

# Tool definitions in Claude API format
CLAUDE_TOOLS = [
    {
        "name": "create_plot",
        "description": "Create and display a matplotlib plot for climate data visualization. Supports line plots, bar charts, scatter plots, heatmaps, and contour plots. The plot will be displayed directly in the chat interface.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plot_config": {
                    "type": "string",
                    "description": "JSON string containing plot configuration with keys: 'plot_type' (line/bar/scatter/heatmap/contour), 'data' (dict with x, y, z arrays), 'title', 'xlabel', 'ylabel', 'style' (optional dict with color, marker, etc.). Example: {\"plot_type\": \"bar\", \"data\": {\"x\": [\"Jan\", \"Feb\", \"Mar\"], \"y\": [10, 20, 15]}, \"title\": \"Monthly Data\", \"xlabel\": \"Month\", \"ylabel\": \"Value\"}"
                }
            },
            "required": ["plot_config"]
        }
    },
    {
        "name": "browse_spear_directory",
        "description": "Browse and explore the SPEAR climate data directory structure. Use this to see what scenarios, ensemble members, frequencies, and variables are available at different levels of the data hierarchy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from SPEAR base (e.g., '' for root, 'historical' for historical scenario, 'historical/r1i1p1f1/Amon' for monthly data). Leave empty to browse the root."
                }
            },
            "required": []
        }
    },
    {
        "name": "search_spear_variables",
        "description": "Search for climate variables across SPEAR datasets. Use this to find specific variables like temperature (tas), precipitation (pr), etc. across different scenarios and frequencies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "description": "Climate scenario: either 'historical' or 'scenarioSSP5-85'",
                    "enum": ["historical", "scenarioSSP5-85"]
                },
                "variable_pattern": {
                    "type": "string",
                    "description": "Pattern to match variable names (e.g., 'tas' for temperature, 'pr' for precipitation, 'ua' for wind). Leave empty to see all variables."
                },
                "frequency": {
                    "type": "string",
                    "description": "Data frequency: 'Amon' for monthly, 'day' for daily, etc. Leave empty to search across all frequencies."
                }
            },
            "required": ["scenario"]
        }
    },
    {
        "name": "get_s3_file_metadata_only",
        "description": "Get detailed metadata about a specific SPEAR NetCDF file without loading the actual data arrays. Shows dimensions, coordinates, variable attributes, time ranges, and spatial coverage. Use this to understand file structure before querying data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "description": "Either 'historical' or 'scenarioSSP5-85'"
                },
                "ensemble_member": {
                    "type": "string",
                    "description": "Ensemble member (e.g., 'r1i1p1f1', 'r15i1p1f1')"
                },
                "frequency": {
                    "type": "string",
                    "description": "'Amon' for monthly, 'day' for daily"
                },
                "variable": {
                    "type": "string",
                    "description": "Variable name (e.g., 'tas', 'pr', 'ua')"
                },
                "grid": {
                    "type": "string",
                    "description": "Grid type (typically 'gr3')"
                },
                "version": {
                    "type": "string",
                    "description": "Data version (typically 'v20210201')"
                }
            },
            "required": ["scenario", "variable"]
        }
    },
    {
        "name": "query_netcdf_data",
        "description": "Query and retrieve actual climate data from SPEAR NetCDF files with optional spatial and temporal subsetting. Use this to get real climate data values for analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "variable": {
                    "type": "string",
                    "description": "Variable name (e.g., 'tas' for temperature, 'pr' for precipitation)"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM format (e.g., '2020-01'). Leave null for beginning of dataset."
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM format (e.g., '2021-12'). Leave null for end of dataset."
                },
                "lat_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[min_latitude, max_latitude] in degrees. E.g., [30, 50] for mid-latitudes. Leave null for global."
                },
                "lon_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[min_longitude, max_longitude] in degrees. E.g., [-120, -80] for North America. Leave null for global."
                },
                "scenario": {
                    "type": "string",
                    "description": "Either 'historical' or 'scenarioSSP5-85'"
                },
                "ensemble_member": {
                    "type": "string",
                    "description": "Ensemble member (default: 'r15i1p1f1')"
                },
                "frequency": {
                    "type": "string",
                    "description": "'Amon' for monthly, 'day' for daily (default: 'Amon')"
                },
                "grid": {
                    "type": "string",
                    "description": "Grid type (default: 'gr3')"
                },
                "version": {
                    "type": "string",
                    "description": "Data version (default: 'v20210201')"
                },
                "chunk_index": {
                    "type": "integer",
                    "description": "Which chunk to return if data is chunked (default: 0)"
                }
            },
            "required": ["variable"]
        }
    }
]
