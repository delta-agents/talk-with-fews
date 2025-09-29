from talk_with_fews.models import GetParameterInput, GetParameterOutput
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.parameter_search import search_parameters
from tests.utils_tests import setup_dot_env
import asyncio


def test_search_parameters():
    """
    Test the get_locations function to ensure it retrieves locations details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    user_settings = setup_dot_env()
    # Create a mock RunContext and input
    # timeseries_search_input = TimeSeriesSearchInput(module_instance="im.wiwb.knmi")
    # Call the function
    ctx = get_runtime_ctx(user_settings)
    input = GetParameterInput(number_of_parameters=10)
    output: GetParameterOutput = asyncio.run(search_parameters(ctx, input))

    ctx = get_runtime_ctx(user_settings)
    input2 = GetParameterInput(filter_parameters_name="H", number_of_parameters=10)
    output2: GetParameterOutput = asyncio.run(search_parameters(ctx, input2))

    # Assert the output is of the expected type
    assert isinstance(output, GetParameterOutput)
    assert output.parameters is not None
    assert len(output.parameters) > 1  # Expecting many results

    assert isinstance(output2, GetParameterOutput)
    assert output2.parameters is not None
    assert len(output2.parameters) > 0  # Expecting at least one result
