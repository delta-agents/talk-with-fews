from talk_with_fews.models.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_parameters
from tests.utils_tests import setup_dot_env
from tests.test_data_helpers import get_test_assertion_data
import asyncio


def test_get_parameter_details():
    """
    Test the get_parameter_details function to ensure it retrieves parameter details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    user_settings = setup_dot_env()
    test_data = get_test_assertion_data()

    # Create a mock RunContext and input
    input_data = GetParameterInput(
        number_of_parameters=test_data["expected_parameter_count"]
    )

    # Call the function
    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_parameters(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetParameterOutput)
    assert output.parameters is not None
    assert len(output.parameters) == test_data["expected_parameter_count"]
    assert isinstance(output.markdown_content, str)
