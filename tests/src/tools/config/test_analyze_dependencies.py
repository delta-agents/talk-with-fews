from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.dependency_analysis import analyze_dependencies
from talk_with_fews.models import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_analyze_dependencies():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    analyze_dependencies_input = DependencyAnalysisInput(
        entity_type="transformation",
        entity_id=1,
        direction="downstream",
    )

    analyze_dependencies_output: DependencyAnalysisOutput = asyncio.run(
        analyze_dependencies(ctx=ctx, input=analyze_dependencies_input)
    )
    assert isinstance(analyze_dependencies_output, DependencyAnalysisOutput)
