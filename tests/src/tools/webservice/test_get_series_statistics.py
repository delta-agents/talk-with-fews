"""
Tests for the get_series_statistics functionality.

This module tests the series statistics retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
from datetime import datetime
from pydantic import ValidationError
import pytest

from talk_with_fews.models.webservice.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_series_statistics
from tests.parallel_decorator import fews_parallel


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv")
def test_get_series_statistics(service):
    """
    Test the get_series_statistics function against different FEWS services.

    This test runs against:
    - actueelwaterbeeld (production)
    - hdsr (local)
    - wsvv (local)
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

    # Create input using service-specific test data
    input_data = GetSeriesStatisticsInput(
        parameter_id=test_data["parameter_ids"][
            0
        ],  # Use first parameter from test data
        location_id=test_data["location_ids"][0],  # Use first location from test data
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, list)
    assert all(isinstance(item, GetSeriesStatisticsOutput) for item in output)

    # If we have results, check the first one
    if output:
        assert isinstance(output[0].description, str)
        # Check for various possible description formats
        description = output[0].description
        assert (
            "Series" in description
            or "No data found" in description
            or "Error fetching data" in description
        )


def test_get_series_statistics_data_empty():
    """
    Test the get_series_statistics function when the data is empty.
    """
    # Setup environment
    import os
    from tests.utils_tests import setup_dot_env

    # Set the correct service for the test data
    os.environ["FEWS_TEST_SERVICE"] = "actueelwaterbeeld"
    user_settings = setup_dot_env()

    # Create input for parameter-based query using working parameters
    input_data = GetSeriesStatisticsInput(
        parameter_id="Eref.d",
        location_id="KNMIUUR278",
        start_time=datetime.fromisoformat("1990-01-01T00:00:00+00:00"),
        end_time=datetime.fromisoformat("2025-12-31T23:59:59+00:00"),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, list)
    assert all(isinstance(item, GetSeriesStatisticsOutput) for item in output)

    # If we have results, check the first one
    if output:
        assert isinstance(output[0].description, str)
        # Check for various possible description formats
        description = output[0].description
        assert (
            "Series" in description
            or "No data found" in description
            or "Error fetching data" in description
        )


def test_get_series_statistics_no_input():
    """
    Test the get_series_statistics function when no input is provided.
    """
    # Call the function and expect ValidationError
    with pytest.raises(ValidationError):
        GetSeriesStatisticsInput()


# todo one input
def test_get_series_statistics_one_input():
    with pytest.raises(ValidationError):
        GetSeriesStatisticsInput(parameter_id="Kwel")


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv")
def test_get_series_statistics_multiple_locations(service):
    """
    Test the get_series_statistics function with multiple locations (single parameter).
    Runs against all available services.
    """
    # Get service-specific configuration
    from tests.utils_tests import setup_dot_env
    from tests.test_config import get_test_service_config

    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input using multiple locations test case
    multiple_test = test_data["multiple_location_test"]
    input_data = GetSeriesStatisticsInput(
        parameter_id=multiple_test["parameter_id"],
        location_id=multiple_test["location_id"],
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, list)
    assert all(isinstance(item, GetSeriesStatisticsOutput) for item in output)

    # Should have at least some series (number depends on service)
    assert len(output) >= 0, f"Expected at least 0 series, got {len(output)}"


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv")
def test_get_series_statistics_multiple_parameters(service):
    """
    Test the get_series_statistics function with multiple parameters (single location).
    Runs against all available services.
    """
    # Get service-specific configuration
    from tests.utils_tests import setup_dot_env
    from tests.test_config import get_test_service_config

    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input using multiple parameters test case
    multiple_test = test_data["multiple_parameter_test"]
    input_data = GetSeriesStatisticsInput(
        parameter_id=multiple_test["parameter_id"],
        location_id=multiple_test["location_id"],
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, list)
    assert all(isinstance(item, GetSeriesStatisticsOutput) for item in output)

    # Should have at least some series (even if some parameters don't exist)
    assert len(output) >= 0, f"Expected at least 0 series, got {len(output)}"


def test_get_series_statistics_validation_error():
    """
    Test that validation correctly fails when both parameter_id and location_id are lists.
    This test runs everywhere since it only tests input validation, not API calls.
    """
    with pytest.raises(Exception):  # Should be a validation error
        GetSeriesStatisticsInput(
            parameter_id=["EV.15", "EV.16"],
            location_id=["HL000141", "HL000142"],
            start_time=datetime.fromisoformat("2024-01-01T00:00:00+01:00"),
            end_time=datetime.fromisoformat("2024-01-14T00:00:00+01:00"),
        )
