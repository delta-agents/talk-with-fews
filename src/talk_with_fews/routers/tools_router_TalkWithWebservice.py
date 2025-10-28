from fastapi import APIRouter
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from talk_with_fews.utils.docstring_generator import auto_docstring
from talk_with_fews.routers.setup_connections import (
    get_runtime_ctx,
    get_user_settings,
    setup_env,
)


# Import tool functions and their models
from talk_with_fews.tools.webservice.get_webservice_info import (
    get_webservice_info as get_webservice_info_pydantic_ai,
)
from talk_with_fews.models.webservice.get_webservice_info import (
    GetWebServiceInfoInput,
    GetWebServiceInfoOutput,
)
from talk_with_fews.tools.webservice.query_webservice_cache import (
    query_webservice_cache as query_webservice_cache_pydantic_ai,
)
from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.tools.webservice.get_parameters import (
    get_parameters as get_parameters_pydantic_ai,
)
from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.tools.webservice.get_locations import (
    get_locations as get_locations_pydantic_ai,
)
from talk_with_fews.models.webservice.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.tools.webservice.get_series_headers import (
    get_series_headers as get_series_headers_pydantic_ai,
)
from talk_with_fews.models.webservice.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.tools.webservice.get_series_statistics import (
    get_series_statistics as get_series_statistics_pydantic_ai,
)
from talk_with_fews.models.webservice.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.tools.webservice.get_series_data import (
    get_series_data as get_series_data_pydantic_ai,
)
from talk_with_fews.models.webservice.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
)
from talk_with_fews.tools.webservice.analyze_flags import (
    analyze_series_flags as analyze_series_flags_pyantic_ai,
)
from talk_with_fews.models.webservice.flags.io import (
    SeriesFlagsInput,
    SeriesFlagsOutput,
)

tokens = setup_env()
verifier = StaticTokenVerifier(tokens=tokens, required_scopes=["read:data"])

# Setup router & auth
router = APIRouter()
mcp = FastMCP("TalkWithFewsWebservice", auth=verifier)


# get_user_info tool registration
@mcp.tool()
@router.post("/tools.webservice/get_webservice_info")
@auto_docstring(
    "Call this at the start of the conversation to return information about the configured FEWS webservice for the given user."
)
async def get_webservice_info(input: GetWebServiceInfoInput) -> GetWebServiceInfoOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)

    return await get_webservice_info_pydantic_ai(ctx, input)


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools.webservice/get_parameters")
@auto_docstring(
    "Get information about parameters. This is how to access parameters data."
    "By default 10 parameters are returned. "
    "If no query is provided, the first number parameters asked for are returned."
    "If a query is provided, the parameters are filtered by the query string."
)
async def get_parameters(
    input: GetParameterInput,
) -> GetParameterOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)

    return await get_parameters_pydantic_ai(ctx, input)


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
async def get_locations(
    input: GetLocationInput,
) -> GetLocationOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_locations_pydantic_ai(ctx, input)


# query_webservice_cache tool registration
@mcp.tool()
@router.post("/tools.webservice/query_webservice_cache")
@auto_docstring(
    """Execute SQL queries against the cached FEWS webservice database (DuckDB).

This tool queries the webservice cache containing:
- series_headers: Available time series combinations
- locations: FEWS location data
- parameters: FEWS parameter data

Note: This queries the DuckDB cache, not the SQLite config database.

SPATIAL ANALYSIS - CRITICAL COORDINATE SYSTEM INFORMATION:

WARNING: The geom column is stored in EPSG:4326 (WGS84) coordinates (degrees).
For accurate spatial analysis with distance calculations, buffers, and spatial joins,
you MUST transform coordinates to EPSG:28992 (Dutch RD system) which uses meters.

CORRECT spatial analysis pattern:
```sql
-- Transform to Dutch coordinate system for accurate distance calculations
SELECT
    locationId,
    shortName,
    ST_Distance(
        ST_Transform(geom, 'EPSG:4326', 'EPSG:28992'),  -- Transform to EPSG:28992 (meters)
        ST_Transform(ST_Point(5.6667, 52.0333), 'EPSG:4326', 'EPSG:28992')  -- Transform point to EPSG:28992
    ) as distance_meters
FROM locations
WHERE ST_DWithin(
    ST_Transform(geom, 'EPSG:4326', 'EPSG:28992'),  -- Transform to EPSG:28992
    ST_Transform(ST_Point(5.6667, 52.0333), 'EPSG:4326', 'EPSG:28992'),  -- Transform point to EPSG:28992
    1000  -- 1000 meters buffer
)
```

INCORRECT (will give results in degrees, not meters):
```sql
SELECT ST_Distance(geom, ST_Point(5.6667, 52.0333)) FROM locations  -- WRONG!
```

Coordinate Systems:
- EPSG:4326 (WGS84): Stored geometry - degrees (lat/lon)
- EPSG:28992 (Dutch RD): Use for spatial analysis - meters

Spatial Functions: All ST_* functions work, but use ST_Transform(geom, 'EPSG:4326', 'EPSG:28992') for analysis.
To return geometry data: use ST_AsText(geom) for WGS84 or ST_AsText(ST_Transform(geom, 'EPSG:4326', 'EPSG:28992')) for RD."""
)
async def query_webservice_cache(input: SQLQueryInput) -> SQLQueryOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await query_webservice_cache_pydantic_ai(ctx, input)


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
async def get_series_headers(
    input: GetSeriesHeadersInput,
) -> GetSeriesHeadersOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_series_headers_pydantic_ai(ctx, input)


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
async def get_series_statistics(
    input: GetSeriesStatisticsInput,
) -> GetSeriesStatisticsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_series_statistics_pydantic_ai(ctx, input)


# get_series_data tool registration
@mcp.tool()
@router.post("/tools.webservice/get_series_data")
@auto_docstring(
    "Get timeseries data for a specific location-parameter combination. "
    "Must query by parameter ID AND location ID, make sure the combination exists using get_series_headers first."
    "Features include: "
    "- Query by location ID and parameter ID "
)
async def get_series_data(input: GetSeriesDataInput) -> GetSeriesDataOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_series_data_pydantic_ai(ctx, input)


# analyze_series_flags tool registration
@mcp.tool()
@router.post("/tools.webservice/analyze_series_flags")
@auto_docstring(
    "Analyze FEWS quality flags for a specific location-parameter combination. "
    "This tool analyzes existing quality flags in the timeseries. "
    "Features include: "
    "- Detailed flag distribution (counts and percentages) "
    "- Quality level summary (Reliable/Doubtful/Unreliable) "
    "- Origin tracking (Original/Corrected/Completed) "
    "- Complete flag descriptions and metadata "
    "\n"
    "Requirements: "
    "- Must provide location ID and parameter ID "
    "- Time range cannot be in the future "
    "- Start time must be before end time "
    "\n"
    "Example Use Cases: "
    "- Monitor data quality across different periods "
    "- Compare quality between locations/parameters "
    "- Identify problematic data sources"
)
async def analyze_series_flags(input: SeriesFlagsInput) -> SeriesFlagsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await analyze_series_flags_pyantic_ai(ctx, input)


# from typing import Optional, List
# from pydantic import BaseModel, Field
# from talk_with_fews.models.base import LaxBaseModel


# class UserInfo(BaseModel):
#     name: str = Field(..., description="dit is de naam van de user")


# class GetUserInfoInput(LaxBaseModel):
#     """
#     Input model for get_info tool.
#     """

#     text: str = Field(..., description="1 woord met het gevoel wat je nu hebt")
#     value: int = Field(..., description="1 getal (integer) welke je nu voelt")
#     boolean: bool = Field(
#         ...,
#         description="dit is een boolean input voor de tool, vul hier True of False in",
#     )
#     list: Optional[List[str]] = Field(
#         None,
#         description="dit is een optionele lijst van str input voor de tool, vul hier een paar woorden in die je nu voelt",
#     )
#     user_name: str = Field(..., description="dit is de naam van de user")


# class GetUserInfoOutput(LaxBaseModel):
#     """
#     Input model for get_info tool.
#     """

#     text: str = Field(..., description="dit is de text output van de tool")
#     value: int = Field(..., description="dit is het getal (integer) output van de tool")
#     list: Optional[List[str]] = Field(
#         None, description="dit is een optionele lijst van str output van de tool"
#     )
#     boolean: bool = Field(..., description="dit is een boolean output van de tool")
#     user: UserInfo = Field(..., description="dit is de user info output van de tool")


# # get_user_info tool registration
# @mcp.tool()
# @router.post("/tools.webservice/user_info")
# @auto_docstring("Get user info")
# async def user_info(input: GetUserInfoInput) -> GetUserInfoOutput:
#     out = GetUserInfoOutput(
#         text=input.text,
#         value=input.value + 2,
#         list=input.list,
#         boolean=input.boolean,
#         user=UserInfo(name=input.user_name),
#     )
#     return out
