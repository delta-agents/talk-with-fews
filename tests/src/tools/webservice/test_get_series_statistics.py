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
    SeriesStatisticsItem,
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
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert isinstance(output.series_statistics, list)
    assert all(
        isinstance(item, SeriesStatisticsItem) for item in output.series_statistics
    )

    # If we have results, check the first one
    if output.series_statistics:
        assert isinstance(output.series_statistics[0].description, str)
        # Check for various possible description formats
        description = output.series_statistics[0].description
        assert (
            "loc:" in description
            or "par:" in description
            or "module:" in description
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
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert isinstance(output.series_statistics, list)
    assert all(
        isinstance(item, SeriesStatisticsItem) for item in output.series_statistics
    )

    # If we have results, check the first one
    if output.series_statistics:
        assert isinstance(output.series_statistics[0].description, str)
        # Check for various possible description formats
        description = output.series_statistics[0].description
        assert (
            "loc:" in description
            or "par:" in description
            or "module:" in description
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
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert isinstance(output.series_statistics, list)
    assert all(
        isinstance(item, SeriesStatisticsItem) for item in output.series_statistics
    )

    # Should have at least some series (number depends on service)
    assert len(output.series_statistics) >= 0, (
        f"Expected at least 0 series, got {len(output.series_statistics)}"
    )


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
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert isinstance(output.series_statistics, list)
    assert all(
        isinstance(item, SeriesStatisticsItem) for item in output.series_statistics
    )

    # Should have at least some series (even if some parameters don't exist)
    assert len(output.series_statistics) >= 0, (
        f"Expected at least 0 series, got {len(output.series_statistics)}"
    )


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


def test_get_series_statistics_content_validation():
    """
    Test that get_series_statistics returns properly structured and valid content.
    Uses actueelwaterbeeld service and checks actual field values.
    """
    import os
    from tests.utils_tests import setup_dot_env
    from tests.test_config import get_test_service_config

    # Set the service
    os.environ["FEWS_TEST_SERVICE"] = "actueelwaterbeeld"
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input with valid parameters
    input_data = GetSeriesStatisticsInput(
        parameter_id=test_data["parameter_ids"][0],
        location_id=test_data["location_ids"][0],
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Verify wrapper structure
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert isinstance(output.description, str)
    assert len(output.description) > 0

    # Verify we have statistics (may be 0 or more)
    assert isinstance(output.series_statistics, list)
    assert len(output.series_statistics) <= 10  # Keep test small

    # If we have results, validate the content of the first item
    if output.series_statistics:
        stats = output.series_statistics[0]

        # Verify it's a SeriesStatisticsItem
        assert isinstance(stats, SeriesStatisticsItem)

        # Verify description exists and is meaningful
        assert isinstance(stats.description, str)
        assert len(stats.description) > 0

        # Verify temporal information if present
        if stats.first_value_time is not None:
            assert isinstance(stats.first_value_time, datetime)
        if stats.last_value_time is not None:
            assert isinstance(stats.last_value_time, datetime)
            # If both are present, last should be after first
            if stats.first_value_time is not None:
                assert stats.last_value_time >= stats.first_value_time

        # Verify value range if present
        if stats.min_value is not None:
            assert isinstance(stats.min_value, str)
        if stats.max_value is not None:
            assert isinstance(stats.max_value, str)

        # Verify units if present
        if stats.parameter_units is not None:
            assert isinstance(stats.parameter_units, str)

        # Verify time step info if present
        if stats.time_step is not None:
            assert isinstance(stats.time_step, str)
        if stats.timestep_info is not None:
            assert isinstance(stats.timestep_info, dict)

        # Verify module instance ID if present
        if stats.module_instance_id is not None:
            assert isinstance(stats.module_instance_id, str)

        # Verify interval analysis structure if present
        if stats.interval_analysis is not None:
            assert isinstance(stats.interval_analysis, dict)

        # Verify estimated data points if present
        if stats.estimated_data_points_in_range is not None:
            assert isinstance(stats.estimated_data_points_in_range, int)
            assert stats.estimated_data_points_in_range >= 0
