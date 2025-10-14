from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_locations
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_locations():
    """
    Test the get_locations function to ensure it retrieves locations details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    user_settings = setup_dot_env()
    # Create a mock RunContext and input
    input_data = GetLocationInput(number_of_locations=6)
    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_locations(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetLocationOutput)
    assert output.locations is not None
    assert len(output.locations) == 6  # > accounts for additions in the future
    assert isinstance(output.description, str)
    assert (
        "retrieved sample locations" in output.description
        or "Found" in output.description
    )


def test_get_locations_query():
    """
    Test the get_locations function to ensure it retrieves locations details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    user_settings = setup_dot_env()
    # Create a mock RunContext and input
    input_data = GetLocationInput(
        number_of_locations=6,
        filter_locations_name="ede",
    )

    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_locations(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetLocationOutput)
    assert output.locations is not None
    assert len(output.locations) <= 6  # May be fewer results with filter
    assert isinstance(output.description, str)
    assert "Found" in output.description or "No locations found" in output.description
