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
from talk_with_fews.tools.config.timeseries_describe import describe_timeseries
from talk_with_fews.models.timeseries_describe import (
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from talk_with_fews.tools.config.timeseries_search import search_timeseries
from talk_with_fews.models.timeseries_search import TimeSeriesSearchOutput
from talk_with_fews.tools.config.transformation_search import search_transformations
from talk_with_fews.models.transformation_search import (
    TransformationSearchInput,
    TransformationSearchOutput,
)
from talk_with_fews.tools.config.workflow_search import search_workflows
from talk_with_fews.models.workflow_search import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
)
from talk_with_fews.tools.config.workflows_details import get_workflow_details
from talk_with_fews.models.workflow_details import (
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from talk_with_fews.tools.config.dead_point_analysis import analyze_dead_points
from talk_with_fews.models.dead_point_analysis import (
    DeadPointsAnalysisInput,
    DeadPointsAnalysisOutput,
)
from talk_with_fews.tools.config.dependency_analysis import analyze_dependencies
from talk_with_fews.models.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.tools.config.get_database_schema import get_database_schema
from talk_with_fews.models.database_schema import (
    DatabaseSchemaInput,
    DatabaseSchemaOutput,
)
from talk_with_fews.tools.config.graph_visualize import visualize_graph
from talk_with_fews.models.graph import (
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.models.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.tools.config.transformation_details import (
    get_transformation_details,
)
from talk_with_fews.models.transformation_details import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
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
async def timeseries_description(
    input: DescribeTimeSeriesInput,
) -> DescribeTimeSeriesOutput:
    # TODO: add authentication passing to the get_runtime
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await describe_timeseries(ctx, input)


# search_timeseries tool registration
@mcp.tool()
@router.post("/tools.config/search_timeseries")
@auto_docstring(
    "Search for time series sets by parameter, qualifier, module, or endpoint status."
)
async def timeseries_search(
    input: TimeSeriesSearchOutput,
) -> TimeSeriesSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_timeseries(ctx, input)


# search_transformations tool registration
@mcp.tool()
@router.post("/tools.config/search_transformations")
@auto_docstring("Search for transformations matching the given criteria.")
async def transformations_search(
    input: TransformationSearchInput,
) -> TransformationSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_transformations(ctx, input)


# search_workflows tool registration
@mcp.tool()
@router.post("/tools.config/search_workflows")
@auto_docstring("Search for workflows by name pattern.")
async def workflows_search(input: WorkflowSearchInput) -> WorkflowSearchOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await search_workflows(ctx, input)


# get_workflow_details tool registration
@mcp.tool()
@router.post("/tools.config/get_workflow_details")
@auto_docstring(
    "Get detailed information about a specific workflow, including its module instance calls and their transformations in sequential order."
)
async def workflow_details(
    input: WorkflowDetailsInput,
) -> WorkflowDetailsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_workflow_details(ctx, input)


# analyze_dead_points tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dead_points")
@auto_docstring(
    "Identify 'dead points' in the FEWS configuration - time series sets that are neither used as inputs for any transformation nor marked as endpoints."
)
async def dead_points_analysis(
    input: DeadPointsAnalysisInput,
) -> DeadPointsAnalysisOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await analyze_dead_points(ctx, input)


# analyze_dependencies tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dependencies")
@auto_docstring(
    "Analyze dependencies for a specific entity, showing both upstream and downstream relationships."
)
async def dependencies_analysis(
    input: DependencyAnalysisInput,
) -> DependencyAnalysisOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await analyze_dependencies(ctx, input)


# get_database_schema tool registration
@mcp.tool()
@router.post("/tools.config/get_database_schema")
@auto_docstring(
    "Get the database schema information to understand the structure of the FEWS configuration database."
)
async def database_schema(input: DatabaseSchemaInput) -> DatabaseSchemaOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_database_schema(ctx, input)


# visualize_graph tool registration
@mcp.tool()
@router.post("/tools.config/visualize_graph")
@auto_docstring(
    "Generate a graph visualization of FEWS entities and their relationships."
)
async def graph_visualization(
    input: GraphVisualizationInput,
) -> GraphVisualizationOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await visualize_graph(ctx, input)


# execute_query tool registration
@mcp.tool()
@router.post("/tools.config/execute_query")
@auto_docstring("Execute a SQL query against the FEWS configuration database.")
async def query_execution(input: SQLQueryInput) -> SQLQueryOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await execute_query(ctx, input)


# get_transformation_details tool registration
@mcp.tool()
@router.post("/tools.config/get_transformation_details")
@auto_docstring("Get detailed information about a specific transformation.")
async def transformation_details(
    input: TransformationDetailsInput,
) -> TransformationDetailsOutput:
    user_settings: dict = get_user_settings(verifier)
    ctx = get_runtime_ctx(user_settings)
    return await get_transformation_details(ctx, input)
