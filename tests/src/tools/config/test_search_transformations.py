from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.transformation_search import search_transformations
from talk_with_fews.models import (
    TransformationSearchInput,
    TransformationSearchOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_search_transformations():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    transformation_search_input = TransformationSearchInput(
        description_pattern="knmi",
    )

    transformation_search_output: TransformationSearchOutput = asyncio.run(
        search_transformations(ctx=ctx, input=transformation_search_input)
    )
    assert isinstance(transformation_search_output, TransformationSearchOutput)
    assert transformation_search_output.results is not None
