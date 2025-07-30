from fastapi import APIRouter
from fastmcp import FastMCP
from talk_with_fews.utils.docstring_generator import auto_docstring


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
from talk_with_fews.models.dead_point_analysis import DeadPointsAnalysisOutput
from talk_with_fews.tools.config.dependency_analysis import analyze_dependencies
from talk_with_fews.models.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.tools.config.get_database_schema import get_database_schema
from talk_with_fews.models.database_schema import DatabaseSchemaOutput
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
from talk_with_fews.routers.setup_connections import get_runtime_ctx

router = APIRouter()
mcp = FastMCP("TalkWithFewsConfig")


# describe_timeseries tool registration
@mcp.tool()
@router.post("/tools.config/describe_timeseries")
@auto_docstring(
    "Get a complete description of a time series, including its basic properties and optionally any transformations that use it as input or output."
)
async def describe_timeseries_mcp(
    input: DescribeTimeSeriesInput,
) -> DescribeTimeSeriesOutput:
    ctx = get_runtime_ctx()
    return await describe_timeseries(ctx, input)


# search_timeseries tool registration
@mcp.tool()
@router.post("/tools.config/search_timeseries")
@auto_docstring(
    "Search for time series sets by parameter, qualifier, module, or endpoint status."
)
async def search_timeseries_mcp(
    input: TimeSeriesSearchOutput,
) -> TimeSeriesSearchOutput:
    ctx = get_runtime_ctx()
    return await search_timeseries(ctx, input)


# search_transformations tool registration
@mcp.tool()
@router.post("/tools.config/search_transformations")
@auto_docstring("Search for transformations matching the given criteria.")
async def search_transformations_mcp(
    input: TransformationSearchInput,
) -> TransformationSearchOutput:
    ctx = get_runtime_ctx()
    return await search_transformations(ctx, input)


# search_workflows tool registration
@mcp.tool()
@router.post("/tools.config/search_workflows")
@auto_docstring("Search for workflows by name pattern.")
async def search_workflows_mcp(input: WorkflowSearchInput) -> WorkflowSearchOutput:
    ctx = get_runtime_ctx()
    return await search_workflows(ctx, input)


# get_workflow_details tool registration
@mcp.tool()
@router.post("/tools.config/get_workflow_details")
@auto_docstring(
    "Get detailed information about a specific workflow, including its module instance calls and their transformations in sequential order."
)
async def get_workflow_details_mcp(
    input: WorkflowDetailsInput,
) -> WorkflowDetailsOutput:
    ctx = get_runtime_ctx()
    return await get_workflow_details(ctx, input)


# analyze_dead_points tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dead_points")
@auto_docstring(
    "Identify 'dead points' in the FEWS configuration - time series sets that are neither used as inputs for any transformation nor marked as endpoints."
)
async def analyze_dead_points_mcp(input: dict = None) -> DeadPointsAnalysisOutput:
    ctx = get_runtime_ctx()
    return await analyze_dead_points(ctx, input)


# analyze_dependencies tool registration
@mcp.tool()
@router.post("/tools.config/analyze_dependencies")
@auto_docstring(
    "Analyze dependencies for a specific entity, showing both upstream and downstream relationships."
)
async def analyze_dependencies_mcp(
    input: DependencyAnalysisInput,
) -> DependencyAnalysisOutput:
    ctx = get_runtime_ctx()
    return await analyze_dependencies(ctx, input)


# get_database_schema tool registration
@mcp.tool()
@router.post("/tools.config/get_database_schema")
@auto_docstring(
    "Get the database schema information to understand the structure of the FEWS configuration database."
)
async def get_database_schema_mcp(input: dict = None) -> DatabaseSchemaOutput:
    ctx = get_runtime_ctx()
    return await get_database_schema(ctx, input)


# visualize_graph tool registration
@mcp.tool()
@router.post("/tools.config/visualize_graph")
@auto_docstring(
    "Generate a graph visualization of FEWS entities and their relationships."
)
async def visualize_graph_mcp(
    input: GraphVisualizationInput,
) -> GraphVisualizationOutput:
    ctx = get_runtime_ctx()
    return await visualize_graph(ctx, input)


# execute_query tool registration
@mcp.tool()
@router.post("/tools.config/execute_query")
@auto_docstring("Execute a SQL query against the FEWS configuration database.")
async def execute_query_mcp(input: SQLQueryInput) -> SQLQueryOutput:
    ctx = get_runtime_ctx()
    return await execute_query(ctx, input)


# get_transformation_details tool registration
@mcp.tool()
@router.post("/tools.config/get_transformation_details")
@auto_docstring("Get detailed information about a specific transformation.")
async def get_transformation_details_mcp(
    input: TransformationDetailsInput,
) -> TransformationDetailsOutput:
    ctx = get_runtime_ctx()
    return await get_transformation_details(ctx, input)
