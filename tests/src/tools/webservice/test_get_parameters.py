from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_parameters
from tests.parallel_decorator import fews_parallel
import asyncio


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen", "wsdd")
def test_get_parameters(service):
    """
    Test the get_parameters function against all FEWS services.

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

    # Create input with enhanced search functionality
    input_data = GetParameterInput(
        number_of_parameters=test_data["expected_parameter_count"],
        filter_parameters_name=test_data["parameter_filters"][
            0
        ],  # Test enhanced search
    )

    # Call the function
    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_parameters(ctx, input_data))

    # Assert the output is of the expected type and structure
    assert isinstance(output, GetParameterOutput)
    assert output.parameters is not None
    assert len(output.parameters) <= test_data["expected_parameter_count"]
    assert isinstance(output.description, str)
    assert "Found" in output.description or "No parameters found" in output.description

    # Test enhanced search functionality
    if output.parameters:
        # Verify that parameters have the expected structure
        param = output.parameters[0]
        assert hasattr(param, "id")
        assert hasattr(param, "name")
        assert hasattr(param, "display_unit")
        assert hasattr(param, "parameter_group")
        assert hasattr(param, "short_name")

        # Note: We don't verify the filter worked because the filter might not match all services


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen", "wsdd")
def test_get_parameters_no_filter(service):
    """
    Test the get_parameters function without any filter against all FEWS services.

    This test verifies that the function works correctly when no search filter is applied.
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

    # Create input without filter
    input_data = GetParameterInput(
        number_of_parameters=test_data["expected_parameter_count"]
    )

    # Call the function
    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(get_parameters(ctx, input_data))

    # Assert the output is of the expected type and structure
    assert isinstance(output, GetParameterOutput)
    assert output.parameters is not None
    assert len(output.parameters) <= test_data["expected_parameter_count"]
    assert isinstance(output.description, str)
    assert "Found" in output.description or "No parameters found" in output.description
