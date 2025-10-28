from talk_with_fews.models.webservice.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_locations
from tests.parallel_decorator import fews_parallel
import asyncio


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_get_locations(service):
    """
    Test the get_locations function against all FEWS services.

    This test runs in parallel against:
    - actueelwaterbeeld (production)
    - hdsr (local)
    - wsvv (local)
    - hhd (local)
    - scheldestromen (local)
    """
    # Set service explicitly
    import os

    os.environ["FEWS_TEST_SERVICE"] = service

    # Get service-specific configuration
    from tests.utils_tests import setup_dot_env
    from tests.test_config import get_test_service_config

    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # this is dependant on the FEWS web service being available indefinitely

    # Create a mock RunContext and input
    input_data = GetLocationInput(
        number_of_locations=test_data["expected_location_count"],
        filter_locations_name=test_data["location_filters"][0],
    )

    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_locations(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetLocationOutput)
    assert output.locations is not None
    assert len(output.locations) <= test_data["expected_location_count"]
    assert isinstance(output.description, str)
    assert "Found" in output.description or "No locations found" in output.description
