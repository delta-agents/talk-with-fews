from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.transformation_details import (
    get_transformation_details,
)
from talk_with_fews.models import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_transformation_details():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    transformation_details_input = TransformationDetailsInput(
        transformation_id=1357,
    )

    transformation_details_output: TransformationDetailsOutput = asyncio.run(
        get_transformation_details(ctx=ctx, input=transformation_details_input)
    )
    assert isinstance(transformation_details_output, TransformationDetailsOutput)
    assert transformation_details_output.results is not None
    assert len(transformation_details_output.results) == 1
