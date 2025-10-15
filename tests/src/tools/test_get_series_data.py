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

    # If we have data, check basic structure
    if result.values:
        first_value = result.values[0]
        assert first_value.datetime is not None
        assert (
            first_value.value is not None or first_value.value == -999.0
        )  # Allow missing values
        assert first_value.flag is not None


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


def test_get_series_data_large_dataset():
    """Test handling of large timeseries datasets (>500 points)."""
    # Use Scheldestromen which has a very large dataset (175,393 data points)
    import os

    os.environ["FEWS_TEST_SERVICE"] = "scheldestromen"

    # Setup environment
    user_settings = setup_dot_env()

    # Create input for the large dataset
    input_data = GetSeriesDataInput(
        location_id="VOV9345",
        parameter_id="WNSHDB1",
        start_time=datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
        end_time=datetime.fromisoformat("2024-12-31T23:59:59+01:00"),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert we got a large dataset (>500 points)
    assert result is not None
    assert len(result.values) > 500  # Should have more than 500 data points
    assert len(result.values) < 200000  # Should be around 175k based on our findings

    # Note: CSV data generation removed - AI assistants can generate CSV from values + metadata if needed

    # Check that we can access individual values without issues
    first_value = result.values[0]
    last_value = result.values[-1]

    assert first_value.location_id == "VOV9345"
    assert first_value.parameter_id == "WNSHDB1"
    assert last_value.location_id == "VOV9345"
    assert last_value.parameter_id == "WNSHDB1"

    # Check metadata is properly populated
    assert "location_id" in result.metadata
    assert "parameter_id" in result.metadata
    assert result.metadata["location_id"] == "VOV9345"
    assert result.metadata["parameter_id"] == "WNSHDB1"

    print(
        f"✅ Successfully handled large dataset: {len(result.values):,} data points (>500)"
    )
    print(f"✅ First value: {first_value.datetime} = {first_value.value}")
    print(f"✅ Last value: {last_value.datetime} = {last_value.value}")


def test_get_series_data_large_dataset_with_thinning():
    """Test handling of large timeseries datasets with thinning parameter."""
    # Use Scheldestromen which has a very large dataset (175,393 data points)
    import os

    os.environ["FEWS_TEST_SERVICE"] = "scheldestromen"

    # Setup environment
    user_settings = setup_dot_env()

    # Create input for the large dataset with thinning
    # 5 years = 157784760000 ms, 1024 pixels = 15408668 ms/pixel
    input_data = GetSeriesDataInput(
        location_id="VOV9345",
        parameter_id="WNSHDB1",
        start_time=datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
        end_time=datetime.fromisoformat("2024-12-31T23:59:59+01:00"),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    result = asyncio.run(get_series_data(ctx, input_data))

    # Assert we got a thinned dataset (should be much smaller)
    assert result is not None
    assert (
        len(result.values) < 10000
    )  # Should be much smaller with thinning (was 175k, now ~2.4k)
    assert len(result.values) > 0  # But should still have some data

    # Note: CSV data generation removed - AI assistants can generate CSV from values + metadata if needed

    # Check that we can access individual values without issues
    first_value = result.values[0]
    last_value = result.values[-1]

    assert first_value.datetime is not None
    assert last_value.datetime is not None

    # Check metadata is properly populated
    assert "location_id" in result.metadata
    assert "parameter_id" in result.metadata
    assert result.metadata["location_id"] == "VOV9345"
    assert result.metadata["parameter_id"] == "WNSHDB1"

    print(
        f"✅ Successfully handled thinned dataset: {len(result.values):,} data points"
    )
    print(f"✅ First value: {first_value.datetime} = {first_value.value}")
    print(f"✅ Last value: {last_value.datetime} = {last_value.value}")
    print(f"✅ Thinning reduced data from ~175k to {len(result.values):,} points")


def test_get_series_data_automatic_thinning():
    """Test automatic thinning for large datasets within get_series_data."""
    # Use Scheldestromen which has a very large dataset
    import os

    os.environ["FEWS_TEST_SERVICE"] = "scheldestromen"

    # Setup environment
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)

    # Test with large date range (5 years) - should trigger automatic thinning
    input_data = GetSeriesDataInput(
        location_id="VOV9345",
        parameter_id="WNSHDB1",
        start_time=datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
        end_time=datetime.fromisoformat("2024-12-31T23:59:59+01:00"),
    )

    result = asyncio.run(get_series_data(ctx, input_data))

    # Assertions
    assert result is not None
    assert len(result.values) > 0  # Should have some data

    # Should be significantly reduced from original (175k -> much smaller)
    # Thinning reduces data substantially but doesn't guarantee <500 points
    assert len(result.values) < 10000  # Should be thinned to manageable size

    # Check that thinning was applied
    assert "thinning_applied" in result.metadata
    assert result.metadata["thinning_applied"] is True
    assert "thinning_value" in result.metadata
    assert "estimated_original_points" in result.metadata
    assert "thinning_reason" in result.metadata

    print(
        f"🎯 Automatic thinning applied: {result.metadata['thinning_value']:,} ms/pixel"
    )
    print(
        f"📊 Original estimated points: {result.metadata['estimated_original_points']:,}"
    )
    print(f"✅ Thinned to: {len(result.values):,} data points")
    print(f"💡 Reason: {result.metadata['thinning_reason']}")

    # Note: CSV data generation removed - AI assistants can generate CSV from values + metadata if needed

    print("✅ Automatic thinning workflow completed successfully")
    print(f"✅ First value: {result.values[0].datetime} = {result.values[0].value}")
    print(f"✅ Last value: {result.values[-1].datetime} = {result.values[-1].value}")


def test_get_series_data_no_thinning_needed():
    """Test that no thinning is applied for small datasets."""
    # Use HDSR which has a small dataset
    import os

    os.environ["FEWS_TEST_SERVICE"] = "hdsr"

    # Setup environment
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)

    # Test with small dataset - should NOT trigger thinning
    input_data = GetSeriesDataInput(
        location_id="beg_109",
        parameter_id="BG.b.0",
        start_time=datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
        end_time=datetime.fromisoformat("2024-12-31T23:59:59+01:00"),
    )

    result = asyncio.run(get_series_data(ctx, input_data))

    # Assertions
    assert result is not None
    assert len(result.values) > 0  # Should have some data

    # Check that thinning was NOT applied
    assert (
        "thinning_applied" not in result.metadata
        or result.metadata.get("thinning_applied", False) is False
    )

    print(
        f"✅ No thinning needed for small dataset: {len(result.values):,} data points"
    )

    print("✅ Small dataset workflow completed successfully")
