from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.parameter_search import search_parameters
from talk_with_fews.models import (
    GetParameterInput,
    GetParameterOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_search_parameters():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    get_parameter_input = GetParameterInput(number_of_parameters=10)

    get_parameter_output: GetParameterOutput = asyncio.run(
        search_parameters(ctx=ctx, input=get_parameter_input)
    )
    assert isinstance(get_parameter_output, GetParameterOutput)
