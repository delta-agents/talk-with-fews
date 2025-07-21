from talk_with_fews.models.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.get_parameters import get_parameters
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_parameter_details():
    """
    Test the get_parameter_details function to ensure it retrieves parameter details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    setup_dot_env()
    # Create a mock RunContext and input
    ctx = get_runtime_ctx()
    input_data = GetParameterInput(number_of_parameters=6)

    # Call the function
    output = asyncio.run(get_parameters(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetParameterOutput)
    assert output.parameters is not None
    assert len(output.parameters) == 6  # > accounts for additions in the future
    assert isinstance(output.markdown_content, str)
