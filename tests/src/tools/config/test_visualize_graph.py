from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.graph_visualize import visualize_graph
from talk_with_fews.models import (
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_visualize_graph():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    graph_visualize_input = GraphVisualizationInput(
        root_entity_id=1,
        root_entity_type="workflow",
    )

    graph_visualize_output: GraphVisualizationOutput = asyncio.run(
        visualize_graph(ctx=ctx, input=graph_visualize_input)
    )
    assert isinstance(graph_visualize_output, GraphVisualizationOutput)
