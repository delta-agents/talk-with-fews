from talk_with_fews.models.transformation_details import (
    TransformationDetails,
    TransformationDetailsInput,
    TransformationDetailsOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.transformation_details import get_transformation_details
from tests.utils_tests import setup_dot_env
import asyncio


def test_transformation_details():
    """
    Test the get_parameter_details function to ensure it retrieves parameter details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    setup_dot_env()
    # Create a mock RunContext and input
    ctx = get_runtime_ctx()
    index = 1  # Example transformation ID, adjust as needed
    input_data = TransformationDetailsInput(transformation_id=index)

    # Call the function
    output = asyncio.run(get_transformation_details(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, TransformationDetailsOutput)
    assert output.results is not None
    assert len(output.results) == 1  # one transformation expected
    transformation: TransformationDetails = output.results[0]
    assert transformation.id == index
    assert (
        transformation.modins == "Peilevaluatie"
    )  # Example module instance, adjust as needed
