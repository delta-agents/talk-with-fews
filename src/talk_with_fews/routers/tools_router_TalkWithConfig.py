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
from talk_with_fews.tools.config.timeseries_describe import (
    describe_timeseries as describe_timeseries_pydantic_ai,
)
from talk_with_fews.models.config.timeseries_describe import (
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from talk_with_fews.tools.config.timeseries_search import (
    search_timeseries as search_timeseries_pydantic_ai,
)
from talk_with_fews.models.config.timeseries_search import TimeSeriesSearchOutput
from talk_with_fews.tools.config.transformation_search import (
    search_transformations as search_transformations_pydantic_ai,
)
from talk_with_fews.models.config.transformation_search import (
    TransformationSearchInput,
    TransformationSearchOutput,
)
from talk_with_fews.tools.config.workflow_search import (
    search_workflows as search_workflows_pydantic_ai,
)
from talk_with_fews.models.config.workflow_search import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
)
from talk_with_fews.tools.config.workflows_details import (
    get_workflow_details as get_workflow_details_pydantic_ai,
)
from talk_with_fews.models.config.workflow_details import (
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from talk_with_fews.tools.config.dead_point_analysis import (
    analyze_dead_points as analyze_dead_points_pydantic_ai,
)
from talk_with_fews.models.config.dead_point_analysis import (
    DeadPointsAnalysisInput,
    DeadPointsAnalysisOutput,
)
from talk_with_fews.tools.config.dependency_analysis import (
    analyze_dependencies as analyze_dependencies_pydantic_ai,
)
from talk_with_fews.models.config.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.tools.config.get_database_schema import (
    get_database_schema as get_database_schema_pydantic_ai,
)
from talk_with_fews.models.config.database_schema import (
    DatabaseSchemaInput,
    DatabaseSchemaOutput,
)
from talk_with_fews.tools.config.graph_visualize import (
    visualize_graph as visualize_graph_pydantic_ai,
)
from talk_with_fews.models.config.graph import (
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from talk_with_fews.tools.config.sql_query import (
    execute_query as execute_query_pydantic_ai,
)
from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.tools.config.transformation_details import (
    get_transformation_details as get_transformation_details_pydantic_ai,
)
from talk_with_fews.models.config.transformation_details import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
)

from talk_with_fews.tools.config.parameter_search import (
    search_parameters as search_parameters_pydantic_ai,
)
from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.tools.config.get_config_info import (
    get_config_info as get_config_info_pydantic_ai,
)
from talk_with_fews.models.config.get_config_info import (
    GetConfigInfoInput,
    GetConfigInfoOutput,
)

tokens = setup_env()
verifier = StaticTokenVerifier(tokens=tokens, required_scopes=["read:data"])

router = APIRouter()
mcp = FastMCP(name="TalkWithFewsConfig", auth=verifier)


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.config/describe_timeseries")
@auto_docstring(
    "Get a complete description of a time series, including its basic properties and optionally any transformations that use it as input or output."
)
async def describe_timeseries(
    input: DescribeTimeSeriesInput,
) -> DescribeTimeSeriesOutput:
    # TODO: add authentication passing to the get_runtime
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await describe_timeseries_pydantic_ai(ctx, input)


# search_timeseries tool registration
@mcp.tool()
@router.post("/tools.config/search_timeseries")
@auto_docstring(
    "Search for time series sets by parameter, qualifier, module, or endpoint status."
)
async def search_timeseries(
    input: TimeSeriesSearchOutput,
) -> TimeSeriesSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_timeseries_pydantic_ai(ctx, input)


# search_transformations tool registration
@mcp.tool()
@router.post("/tools.config/search_transformations")
@auto_docstring("Search for transformations matching the given criteria.")
async def search_transformations(
    input: TransformationSearchInput,
) -> TransformationSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_transformations_pydantic_ai(ctx, input)


# search_workflows tool registration
@mcp.tool()
@router.post("/tools.config/search_workflows")
@auto_docstring("Search for workflows by name pattern.")
async def search_workflows(input: WorkflowSearchInput) -> WorkflowSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_workflows_pydantic_ai(ctx, input)


# get_workflow_details tool registration
@mcp.tool()
@router.post("/tools.config/get_workflow_details")
@auto_docstring(
    "Get detailed information about a specific workflow, including its module instance calls and their transformations in sequential order."
)
async def get_workflow_details(
    input: WorkflowDetailsInput,
) -> WorkflowDetailsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_workflow_details_pydantic_ai(ctx, input)


# analyze_dead_points tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dead_points")
@auto_docstring(
    "Identify 'dead points' in the FEWS configuration - time series sets that are neither used as inputs for any transformation nor marked as endpoints."
)
async def analyze_dead_points(
    input: DeadPointsAnalysisInput,
) -> DeadPointsAnalysisOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await analyze_dead_points_pydantic_ai(ctx, input)


# analyze_dependencies tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dependencies")
@auto_docstring(
    "Analyze dependencies for a specific entity, showing both upstream and downstream relationships."
)
async def analyze_dependencies(
    input: DependencyAnalysisInput,
) -> DependencyAnalysisOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await analyze_dependencies_pydantic_ai(ctx, input)


# get_database_schema tool registration
@mcp.tool()
@router.post("/tools.config/get_database_schema")
@auto_docstring(
    "Get the database schema information to understand the structure of the FEWS configuration database."
)
async def get_database_schema(input: DatabaseSchemaInput) -> DatabaseSchemaOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_database_schema_pydantic_ai(ctx, input)


# visualize_graph tool registration
@mcp.tool()
@router.post("/tools.config/visualize_graph")
@auto_docstring(
    "Generate a graph visualization of FEWS entities and their relationships."
)
async def visualize_graph(
    input: GraphVisualizationInput,
) -> GraphVisualizationOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await visualize_graph_pydantic_ai(ctx, input)


# execute_query tool registration
@mcp.tool()
@router.post("/tools.config/execute_query")
@auto_docstring("Execute a SQL query against the FEWS configuration database.")
async def execute_query(input: SQLQueryInput) -> SQLQueryOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await execute_query_pydantic_ai(ctx, input)


# get_transformation_details tool registration
@mcp.tool()
@router.post("/tools.config/get_transformation_details")
@auto_docstring("Get detailed information about a specific transformation.")
async def get_transformation_details(
    input: TransformationDetailsInput,
) -> TransformationDetailsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_transformation_details_pydantic_ai(ctx, input)


# search_parameters tool registration
@mcp.tool()
@router.post("/tools.config/search_parameters")
@auto_docstring("Look for a given number of parameters, optionally filtered by name.")
async def search_parameters(
    input: GetParameterInput,
) -> GetParameterOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_parameters_pydantic_ai(ctx, input)


# Config info tool registration
@mcp.tool()
@router.post("/tools.config/get_config_info")
@auto_docstring("Retrieve information about the FEWS configuration.")
async def get_config_info(
    input: GetConfigInfoInput,
) -> GetConfigInfoOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_config_info_pydantic_ai(ctx, input)
