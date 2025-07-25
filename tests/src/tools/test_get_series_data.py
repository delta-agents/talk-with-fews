"""
Tests for the get_series_data functionality.

This module tests the timeseries data retrieval for specific location-parameter combinations.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from talk_with_fews.models.get_series_data import GetSeriesDataInput
from talk_with_fews.tools.webservice.get_series_data import get_series_data
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from tests.utils_tests import setup_dot_env


def normalize_line_endings(text: str) -> str:
    """Normalize line endings to \n for consistent comparison."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def test_get_series_data():
    """Test retrieving timeseries data for KNMIUUR278 Eref.d."""
    # Setup environment
    setup_dot_env()

    # Create input
    input_data = GetSeriesDataInput(
        location_id="KNMIUUR278",
        parameter_id="Eref.d",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert
    assert result is not None
    assert len(result.values) == 32  # 31 days in January + 1 February

    # Check metadata
    assert result.metadata["location_id"] == "KNMIUUR278"
    assert result.metadata["parameter_id"] == "Eref.d"
    assert result.metadata["station_name"] == "Heino"
    assert result.metadata["units"] == "mm"
    assert result.metadata["type"] == "accumulative"
    assert result.metadata["moduleinstance_id"] == "im.wiwb.knmi"

    # Check first value
    first_value = result.values[0]
    assert first_value.datetime == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert first_value.location_id == "KNMIUUR278"
    assert first_value.station_name == "Heino"
    assert first_value.parameter_id == "Eref.d"
    assert first_value.moduleinstance_id == "im.wiwb.knmi"
    assert first_value.value == 0.1
    assert first_value.flag == 0

    # Check last value
    last_value = result.values[-1]
    assert last_value.datetime == datetime(2025, 2, 1, tzinfo=timezone.utc)
    assert last_value.value == 0.7

    # Check CSV format
    csv_lines = normalize_line_endings(result.csv_data).strip().split("\n")
    assert len(csv_lines) == 33  # header + 32 data rows
    assert (
        normalize_line_endings(csv_lines[0])
        == "datetime,location_id,station_name,parameter_id,moduleinstance_id,value,flag"
    )

    # Verify a few known values from the example data
    known_values = {
        "2025-01-01": 0.1,
        "2025-01-14": 0.5,
        "2025-01-27": 0.5,
        "2025-01-28": 0.7,
        "2025-02-01": 0.7,
    }

    for value in result.values:
        date_str = value.datetime.strftime("%Y-%m-%d")
        if date_str in known_values:
            assert value.value == known_values[date_str], (
                f"Value mismatch for {date_str}"
            )


def test_get_series_data_missing_values():
    """Test handling of missing values in the timeseries data."""
    # Setup environment
    setup_dot_env()

    # Create input
    input_data = GetSeriesDataInput(
        location_id="KNMIUUR278",
        parameter_id="Eref.d",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert
    # Check that missing values (-999.0 in XML) are converted to None
    for value in result.values:
        assert (
            value.value is not None
        )  # In this example data we don't have missing values
        assert value.value >= 0  # All values should be non-negative for Eref.d


def test_get_series_data_invalid_location():
    """Test error handling for invalid location ID."""
    # Setup environment
    setup_dot_env()

    # Create input
    input_data = GetSeriesDataInput(
        location_id="INVALID_LOCATION",
        parameter_id="Eref.d",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function and expect error
    with pytest.raises(Exception) as exc_info:
        asyncio.run(get_series_data(ctx, input_data))
    assert "Failed to fetch data" in str(exc_info.value)


def test_get_series_data_invalid_parameter():
    """Test error handling for invalid parameter ID."""
    # Setup environment
    setup_dot_env()

    # Create input
    input_data = GetSeriesDataInput(
        location_id="KNMIUUR278",
        parameter_id="INVALID_PARAMETER",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function and expect error
    with pytest.raises(Exception) as exc_info:
        asyncio.run(get_series_data(ctx, input_data))
    assert "Failed to fetch data" in str(exc_info.value)
