from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.dead_point_analysis import analyze_dead_points
from talk_with_fews.models import (
    DeadPointsAnalysisInput,
    DeadPointsAnalysisOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_analyze_dead_points():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    dead_point_analysis_input = DeadPointsAnalysisInput(
        entity_type="transformation",
        entity_id=1,
    )

    dead_point_analysis_output: DeadPointsAnalysisOutput = asyncio.run(
        analyze_dead_points(ctx=ctx, input=dead_point_analysis_input)
    )
    assert isinstance(dead_point_analysis_output, DeadPointsAnalysisOutput)
    assert isinstance(dead_point_analysis_output.dead_points, list)
