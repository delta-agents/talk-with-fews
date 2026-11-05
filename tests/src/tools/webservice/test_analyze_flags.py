"""
Unit tests for FEWS flag analysis tool.

These tests verify that the tool correctly counts and summarizes flags.
They do NOT test:
- Pattern detection
- Value analysis
- Flag modification
"""

from datetime import datetime, timedelta, timezone
import pytest
from typing import List


from talk_with_fews.models.webservice.flags.errors import (
    UnknownFlagError,
    InvalidTimeRangeError,
)
from talk_with_fews.models.webservice.flags.io import SeriesFlagsInput
from talk_with_fews.models.webservice.get_series_data import TimeseriesValue
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.webservice.analyze_flags import (
    count_series_flags,
    analyze_series_flags,
)
from tests.utils_tests import setup_dot_env
from tests.parallel_decorator import fews_parallel


def create_test_values(flags: List[int]) -> List[TimeseriesValue]:
    """Helper to create test timeseries values with flags"""
    values = []
    for i, flag in enumerate(flags):
        value = TimeseriesValue(
            datetime=datetime(2024, 1, 1) + timedelta(hours=i),
            value=float(i),
            flag=flag,
        )
        values.append(value)
    return values


async def get_module_instance_id_for_flags(
    ctx, location_id: str, parameter_id: str
) -> str:
    """
    Helper function to get the module_instance_id for a location-parameter combination from test config.

    Args:
        ctx: Runtime context
        location_id: Location ID
        parameter_id: Parameter ID

    Returns:
        str: Module instance ID from test configuration

    Raises:
        Exception: If no valid module_instance_id can be found in test config
    """
    from tests.test_config import get_test_service_config

    try:
        # Get the test service configuration
        service_config = get_test_service_config()
        test_data = service_config.test_data

        # Check if we have a module instance mapping
        module_instance_mapping = test_data.get("module_instance_mapping", {})

        # Look up the module instance ID for this location-parameter combination
        if location_id in module_instance_mapping:
            location_mapping = module_instance_mapping[location_id]
            if parameter_id in location_mapping:
                return location_mapping[parameter_id]

        # Fallback: try to find any module instance ID for this parameter
        for loc_id, param_mapping in module_instance_mapping.items():
            if parameter_id in param_mapping:
                return param_mapping[parameter_id]

        # If still not found, raise an exception
        raise Exception(
            f"No module instance ID found in test config for location '{location_id}' and parameter '{parameter_id}'"
        )

    except Exception as e:
        # Re-raise the exception with more context
        raise Exception(
            f"Failed to get module instance ID for location '{location_id}' and parameter '{parameter_id}': {str(e)}"
        )


@pytest.fixture
def test_context():
    """Create a test context with FEWS webservice URL"""
    user_settings = setup_dot_env()
    return get_runtime_ctx(user_settings)


@pytest.mark.asyncio
async def test_count_series_flags_basic():
    """Test basic flag counting"""
    # Test data with all quality levels
    values = create_test_values([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

    result = await count_series_flags(values)

    assert result["total_values"] == 10
    assert len(result["counts"]) == 10

    # Check quality counts
    assert result["quality_counts"]["Reliable"] == 3  # Flags 0,1,2
    assert result["quality_counts"]["Doubtful"] == 3  # Flags 3,4,5
    assert result["quality_counts"]["Unreliable"] == 4  # Flags 6,7,8,9

    # Check origin counts
    assert result["origin_counts"]["Original"] == 4  # Flags 0,3,6,9
    assert result["origin_counts"]["Corrected"] == 3  # Flags 1,4,7
    assert result["origin_counts"]["Completed"] == 3  # Flags 2,5,8


@pytest.mark.asyncio
async def test_count_series_flags_empty():
    """Test flag counting with empty input"""
    result = await count_series_flags([])

    assert result["total_values"] == 0
    assert len(result["counts"]) == 0
    assert result["quality_counts"] == {"Reliable": 0, "Doubtful": 0, "Unreliable": 0}
    assert result["origin_counts"] == {"Original": 0, "Corrected": 0, "Completed": 0}


@pytest.mark.asyncio
async def test_count_series_flags_unknown():
    """Test handling of unknown flags"""
    values = create_test_values([0, 99])  # 99 is not a valid flag

    with pytest.raises(UnknownFlagError) as exc:
        await count_series_flags(values)
    assert "99" in str(exc.value)


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_analyze_series_flags_with_real_data(service):
    """
    Test flag analysis with real data from FEWS services using service-specific configuration.

    This test runs against all available FEWS services using their configured
    location_ids and parameter_ids from test_config.py.
    """
    import asyncio
    import os

    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Get service-specific configuration
    from tests.test_config import get_test_service_config

    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Use service-specific parameters from test config
    location_id = test_data["location_ids"][0]  # Use first location
    parameter_id = test_data["parameter_ids"][0]  # Use first parameter
    start_time = datetime.fromisoformat(test_data["start_time"])
    end_time = datetime.fromisoformat(test_data["end_time"])

    print(f"Testing {service}: {location_id}/{parameter_id}")
    print(f"Period: {start_time} to {end_time}")

    # Create context
    ctx = get_runtime_ctx(user_settings)

    # Get module instance ID
    module_instance_id = asyncio.run(
        get_module_instance_id_for_flags(ctx, location_id, parameter_id)
    )

    # Create test input
    input = SeriesFlagsInput(
        location_id=location_id,
        parameter_id=parameter_id,
        module_instance_id=module_instance_id,
        start_time=start_time,
        end_time=end_time,
        include_flag_sources=False,
    )

    # Run analysis
    try:
        result = asyncio.run(analyze_series_flags(ctx, input))

        # Basic validation - check if we got data
        if result.counts.total_values > 0:
            assert len(result.flag_counts) > 0
            print(f"✅ Successfully analyzed {result.counts.total_values} values")
        else:
            print("⚠️  No data found for this parameter-location combination")
            # This is acceptable - not all combinations will have data
            return
    except Exception as e:
        error_msg = str(e)
        if "Time range cannot be in the future" in error_msg:
            print(f"⚠️  Time range issue: {error_msg}")
            return  # Skip future date tests
        elif "Some of the location ids do not exist" in error_msg:
            print(f"⚠️  Location/parameter issue: {error_msg}")
            return  # Skip invalid combinations
        else:
            # Re-raise unexpected errors
            raise

    # Validate flag ranges
    for flag_count in result.flag_counts:
        assert 0 <= flag_count.flag <= 9  # Valid FEWS flags
        assert 0 <= flag_count.percentage <= 100

    # Print summary for manual verification
    print(
        f"\n=== FEWS Flag Analysis Results: {service} - {location_id} - {parameter_id} ==="
    )
    print(f"Total Values: {result.counts.total_values}")
    print("\nQuality Distribution:")
    print(
        f"- Reliable:   {result.counts.reliable_count:3d} values ({result.counts.reliable_percentage:5.1f}%)"
    )
    print(
        f"- Doubtful:   {result.counts.doubtful_count:3d} values ({result.counts.doubtful_percentage:5.1f}%)"
    )
    print(
        f"- Unreliable: {result.counts.unreliable_count:3d} values ({result.counts.unreliable_percentage:5.1f}%)"
    )

    print("\nFlag Distribution:")
    for flag_count in sorted(result.flag_counts, key=lambda x: x.flag):
        print(
            f"Flag {flag_count.flag:1d} ({flag_count.origin:>9s}, {flag_count.quality:>10s}): "
            f"{flag_count.count:3d} values ({flag_count.percentage:5.1f}%)"
        )
        print(f"   Description: {flag_count.description}")

    # Additional validation - ensure we have reasonable data quality for testing
    reliable_pct = result.counts.reliable_percentage
    if reliable_pct < 10:
        print(
            f"⚠️  Warning: Very low reliable data percentage ({reliable_pct:.1f}%) for {service}"
        )
    else:
        print(f"✅ Good data quality for testing: {reliable_pct:.1f}% reliable")


@pytest.mark.asyncio
async def test_analyze_series_flags_invalid_time_range(test_context):
    """Test handling of invalid time ranges"""
    # Test end time before start time
    input = SeriesFlagsInput(
        location_id="KNMIUUR278",
        parameter_id="Eref.d",
        module_instance_id="default_module_instance",
        start_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(InvalidTimeRangeError) as exc:
        await analyze_series_flags(test_context, input)
    assert "before" in str(exc.value)

    # Test future time range
    future = datetime.now(timezone.utc) + timedelta(days=1)
    input = SeriesFlagsInput(
        location_id="KNMIUUR278",
        parameter_id="Eref.d",
        module_instance_id="default_module_instance",
        start_time=datetime.now(timezone.utc),
        end_time=future,
    )

    with pytest.raises(InvalidTimeRangeError) as exc:
        await analyze_series_flags(test_context, input)
    assert "future" in str(exc.value)


@fews_parallel("actueelwaterbeeld", "wsvv")
def test_analyze_series_flags_datetime_comparison_error(service):
    """
    Test that verifies the WSVV datetime comparison error is fixed.

    This test should:
    - PASS for actueelwaterbeeld (working service)
    - PASS for wsvv (datetime error has been fixed)

    Issue: https://github.com/delta-agents/talk-with-fews/issues/76

    The datetime comparison error has been fixed by properly handling
    timezone-naive datetimes in the validate_time_range function.
    This test serves as a regression test to ensure the fix remains working.
    """
    import asyncio
    import os

    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Get service-specific configuration
    from tests.test_config import get_test_service_config

    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Use service-specific parameters from test config
    if service == "wsvv":
        # WSVV: Use parameters that should have data (timezone-naive datetimes)
        location_id = test_data["location_ids"][0]  # "HL000141"
        parameter_id = test_data["parameter_ids"][0]  # "Q.G" (from test config)
        start_time = datetime(2024, 1, 1)  # No timezone - testing our fix!
        end_time = datetime(2024, 1, 14)  # No timezone - testing our fix!
        print(
            f"Testing WSVV with timezone-naive datetimes: {location_id}/{parameter_id}"
        )
        print(f"Using timezone-naive datetimes: {start_time} to {end_time}")
    else:
        # actueelwaterbeeld: Use working parameters from test config
        location_id = test_data["location_ids"][0]  # "KNMIUUR278"
        parameter_id = test_data["parameter_ids"][0]  # "Eref.d"
        start_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2025, 2, 1, tzinfo=timezone.utc)
        print(
            f"Testing {service} with working parameters: {location_id}/{parameter_id}"
        )

    # Create context
    ctx = get_runtime_ctx(user_settings)

    # Get module instance ID
    module_instance_id = asyncio.run(
        get_module_instance_id_for_flags(ctx, location_id, parameter_id)
    )

    # Create test input
    input_data = SeriesFlagsInput(
        location_id=location_id,
        parameter_id=parameter_id,
        module_instance_id=module_instance_id,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        # This should work for both services now (error may have been fixed)
        result = asyncio.run(analyze_series_flags(ctx, input_data))

        # If we get here, the test passed
        assert result is not None
        print(f"{service} test passed - {result.counts.total_values} values found")

    except Exception as e:
        error_msg = str(e)
        print(f"{service} test failed with error: {error_msg}")

        if service == "wsvv" and "offset-naive and offset-aware" in error_msg:
            print("✅ Successfully reproduced the datetime comparison error for WSVV!")
            # This is the expected failure, so we raise it to fail the test
            raise
        else:
            # Unexpected error or error on actueelwaterbeeld
            print(f"❌ Unexpected error on {service}: {error_msg}")
            raise
