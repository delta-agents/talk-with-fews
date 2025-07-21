from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_fews.utils.docstring_generator import auto_docstring


# Import tool functions and their models
from talk_with_fews.tools.sql_query import execute_query_webservice_cache
from talk_with_fews.models.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.tools.get_parameters import get_parameters
from talk_with_fews.models.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.tools.get_locations import get_locations
from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP("TalkWithFewsWebservice")


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools/get_parameters")
@auto_docstring(
    "Get information about all the parameters. These cannot be filtered by location."
)
async def get_parameters_mcp(
    input: GetParameterInput,
) -> GetParameterOutput:
    ctx = get_runtime_ctx()
    return await get_parameters(ctx, input)


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools/get_locations")
@auto_docstring(
    "Get information about all the locations. These can be filtered by parameters."
)
async def get_locations_mcp(
    input: GetLocationInput,
) -> GetLocationOutput:
    ctx = get_runtime_ctx()
    return await get_locations(ctx, input)


# get_parameter_details tool registration
@mcp.tool()
@router.post("/tools/execute_query_webservice")
@auto_docstring(
    "Execute a SQL query on the cached FewsWebService database which contains the locations and parameters from the FEWS web service. This is useful for quick access to parameter and location data."
)
async def execute_query_webservice_mcp(input: SQLQueryInput) -> SQLQueryOutput:
    ctx = get_runtime_ctx()
    return await execute_query_webservice_cache(ctx, input)
