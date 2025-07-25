from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_fews.utils.docstring_generator import auto_docstring
from talk_with_fews.routers.setup_connections import get_runtime_ctx


# Import tool functions and their models
from talk_with_fews.tools.webservice.sql_query_webservice import (
    execute_query_webservice,
)
from talk_with_fews.models.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.tools.webservice.get_parameters import get_parameters
from talk_with_fews.models.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.tools.webservice.get_locations import get_locations
from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.tools.webservice.get_series_headers import get_series_headers
from talk_with_fews.models.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.tools.webservice.get_series_statistics import get_series_statistics
from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.tools.webservice.get_series_data import get_series_data
from talk_with_fews.models.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
)

router = APIRouter()
mcp = FastMCP("TalkWithFewsWebservice")


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools.webservice/get_parameters")
@auto_docstring(
    "Get information about parameters. This is how to access parameters data."
    "By default 10 parameters are returned. "
    "If no query is provided, the first number parameters asked for are returned."
    "If a query is provided, the parameters are filtered by the query string."
)
async def get_parameters_mcp(
    input: GetParameterInput,
) -> GetParameterOutput:
    ctx = get_runtime_ctx()
    return await get_parameters(ctx, input)


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools.webservice/get_locations")
@auto_docstring(
    "Get location information from the FEWS WebService database. "
    "Returns location metadata including coordinates, names, and spatial geometry data. "
    "By default returns 10 locations. "
    "Features: "
    "- Filter locations using query string matching on location names/IDs "
    "- Access spatial geometry data in 'geom' field (EPSG:4326 coordinate system) "
    "- Control result size with limit parameter "
    "- Essential for identifying monitoring sites and their geographic properties"
)
async def get_locations_mcp(
    input: GetLocationInput,
) -> GetLocationOutput:
    ctx = get_runtime_ctx()
    return await get_locations(ctx, input)


# execute_query_webservice tool registration
@mcp.tool()
@router.post("/tools.webservice/execute_query_webservice")
@auto_docstring(
    "Execute SQL queries on the FEWS WebService database containing locations and parameters. "
    "Use this tool to access comprehensive parameter and location data with advanced filtering capabilities. "
    "Features include: "
    "- Full access to all parameters and location metadata "
    "- Spatial queries using DuckDB's geospatial functions (ST_Within, ST_DWithin, ST_Transform) "
    "- Location geometry data stored in 'geom' field (EPSG:4326 coordinate system) "
    "- Complex filtering and aggregation operations "
)
async def execute_query_webservice_mcp(input: SQLQueryInput) -> SQLQueryOutput:
    ctx = get_runtime_ctx()
    return await execute_query_webservice(ctx, input)


# get_series_headers tool registration
@mcp.tool()
@router.post("/tools.webservice/get_series_headers")
@auto_docstring(
    "Get series headers from the FEWS WebService with incremental caching. "
    "Retrieves available time series metadata using an efficient caching strategy. "
    "Features include: "
    "- Query by parameter ID or location ID "
    "- Incremental caching (only fetch when needed) "
    "- Minimal but meaningful output for cost optimization "
    "- User-friendly follow-up suggestions "
    "- Automatic foreign key validation with existing data "
    "- Essential for discovering available time series and their properties"
)
async def get_series_headers_mcp(
    input: GetSeriesHeadersInput,
) -> GetSeriesHeadersOutput:
    ctx = get_runtime_ctx()
    return await get_series_headers(ctx, input)


# get_series_statistics tool registration
@mcp.tool()
@router.post("/tools.webservice/get_series_statistics")
@auto_docstring(
    "Get statistical summaries for time series from the FEWS WebService. "
    "Retrieves statistics such as mean, min, max, and count for specified series. "
    "Features include: "
    "- Must Query by parameter ID AND location ID, make sure the combination exists using get_series_headers first."
    "- Optionally Specify time range for statistics, else defaults 2 days"
    "- Useful for quick data exploration and validation "
    "- Returns summary statistics for each matching series"
)
async def get_series_statistics_mcp(
    input: GetSeriesStatisticsInput,
) -> GetSeriesStatisticsOutput:
    ctx = get_runtime_ctx()
    return await get_series_statistics(ctx, input)


# get_series_data tool registration
@mcp.tool()
@router.post("/tools.webservice/get_series_data")
@auto_docstring(
    "Get timeseries data for a specific location-parameter combination. "
    "Must query by parameter ID AND location ID, make sure the combination exists using get_series_headers first."
    "Features include: "
    "- Query by location ID and parameter ID "
)
async def get_series_data_mcp(input: GetSeriesDataInput) -> GetSeriesDataOutput:
    ctx = get_runtime_ctx()
    return await get_series_data(ctx, input)
