"""
Tests for the get_series_data functionality.

This module tests the timeseries data retrieval for specific location-parameter combinations.
"""

import asyncio
import pytest
from datetime import datetime
from talk_with_fews.models.get_series_data import GetSeriesDataInput
from talk_with_fews.tools.webservice.get_series_data import get_series_data
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from tests.utils_tests import setup_dot_env
from tests.test_config import get_test_service_config


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to \n for consistent comparison."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


# @pytest.mark.skip(reason="Depends on live FEWS data, not suitable for CI")
def test_get_series_data():
    """Test retrieving timeseries data using dynamic test configuration."""
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input using service-specific test data
    t_start = datetime.fromisoformat(test_data["start_time"])
    t_end = datetime.fromisoformat(test_data["end_time"])
    input_data = GetSeriesDataInput(
        location_id=test_data["location_ids"][0],  # Use first location from test data
        parameter_id=test_data["parameter_ids"][
            0
        ],  # Use first parameter from test data
        start_time=t_start,
        end_time=t_end,
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert basic structure
    assert result is not None
    assert len(result.values) >= 0  # Should be non-negative (may have data or be empty)

    # Check metadata structure
    assert "location_id" in result.metadata
    assert "parameter_id" in result.metadata
    assert result.metadata["location_id"] == test_data["location_ids"][0]
    assert result.metadata["parameter_id"] == test_data["parameter_ids"][0]

    # Check CSV format
    csv_lines = normalize_line_endings(result.csv_data).strip().split("\n")
    assert len(csv_lines) >= 1  # At least header row
    assert (
        normalize_line_endings(csv_lines[0])
        == "datetime,location_id,station_name,parameter_id,moduleinstance_id,value,flag"
    )

    # If we have data, check basic structure
    if result.values:
        first_value = result.values[0]
        assert first_value.location_id == test_data["location_ids"][0]
        assert first_value.parameter_id == test_data["parameter_ids"][0]
        assert (
            first_value.value is not None or first_value.value == -999.0
        )  # Allow missing values


def test_get_series_data_missing_values():
    """Test handling of missing values in the timeseries data."""
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input using service-specific test data
    input_data = GetSeriesDataInput(
        location_id=test_data["location_ids"][0],
        parameter_id=test_data["parameter_ids"][0],
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert basic structure
    assert result is not None
    assert len(result.values) >= 0  # Should be non-negative (may have data or be empty)

    # Check that values are properly structured
    for value in result.values:
        assert value.location_id == test_data["location_ids"][0]
        assert value.parameter_id == test_data["parameter_ids"][0]
        # Allow missing values (-999.0) or None
        assert value.value is None or value.value == -999.0 or value.value >= 0


def test_get_series_data_invalid_location():
    """Test error handling for invalid location ID."""
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input with invalid location but valid parameter
    input_data = GetSeriesDataInput(
        location_id="INVALID_LOCATION",
        parameter_id=test_data["parameter_ids"][0],
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function and expect error
    with pytest.raises(Exception) as exc_info:
        asyncio.run(get_series_data(ctx, input_data))
    assert "Failed to fetch data" in str(exc_info.value)


def test_get_series_data_invalid_parameter():
    """Test error handling for invalid parameter ID."""
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input with valid location but invalid parameter
    input_data = GetSeriesDataInput(
        location_id=test_data["location_ids"][0],
        parameter_id="INVALID_PARAMETER",
        start_time=datetime.fromisoformat(test_data["start_time"]),
        end_time=datetime.fromisoformat(test_data["end_time"]),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function and expect error
    with pytest.raises(Exception) as exc_info:
        asyncio.run(get_series_data(ctx, input_data))
    assert "Failed to fetch data" in str(exc_info.value)
