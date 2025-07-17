from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.get_locations import get_locations
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_locations():
    """
    Test the get_locations function to ensure it retrieves locations details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    setup_dot_env()
    # Create a mock RunContext and input
    ctx = get_runtime_ctx()
    input_data = GetLocationInput(show_attributes=True)

    # Call the function
    output = asyncio.run(get_locations(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetLocationOutput)
    assert output.locations is not None
    assert len(output.locations) >= 3805  # > accounts for additions in the future
    assert isinstance(output.markdown_content, str)
    assert "## Locations" in output.markdown_content
