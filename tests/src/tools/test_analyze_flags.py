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
from typing import List, Tuple


from talk_with_fews.models.flags.errors import UnknownFlagError, InvalidTimeRangeError
from talk_with_fews.models.flags.io import SeriesFlagsInput
from talk_with_fews.models.get_series_data import TimeseriesValue
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
            location_id="KNMIUUR278",
            station_name="Test Station",
            parameter_id="Eref.d",
            moduleinstance_id="TEST_MOD",
            value=float(i),
            flag=flag,
        )
        values.append(value)
    return values


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


# @pytest.mark.skip(reason="Uses live FEWS data, not suitable for CI")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location_id,parameter_id,period",
    [
        # KNMI referentie verdamping, verschillende periodes
        (
            "KNMIUUR278",
            "Eref.d",
            (datetime(2025, 1, 1), datetime(2025, 2, 1)),
        ),  # Januari 2025
        (
            "KNMIUUR278",
            "Eref.d",
            (datetime(2025, 6, 1), datetime(2025, 7, 1)),
        ),  # Juni 2025
        # Grondwater kwel, verschillende locaties
        (
            "GPG_1698",
            "Kwel",
            (datetime(2025, 1, 1), datetime(2025, 2, 1)),
        ),  # Januari 2025
        (
            "GPG_10",
            "Kwel",
            (datetime(2025, 1, 1), datetime(2025, 2, 1)),
        ),  # Januari 2025
    ],
)
async def test_analyze_series_flags_with_real_data(
    test_context,
    capsys,
    location_id: str,
    parameter_id: str,
    period: Tuple[datetime, datetime],
):
    """Test flag analysis with real data from FEWS"""
    # Create test input
    start_time, end_time = period
    input = SeriesFlagsInput(
        location_id=location_id,
        parameter_id=parameter_id,
        start_time=start_time.replace(tzinfo=timezone.utc),
        end_time=end_time.replace(tzinfo=timezone.utc),
    )

    # Run analysis
    result = await analyze_series_flags(test_context, input)

    # Basic validation
    assert result.total_values > 0
    assert len(result.flag_counts) > 0
    assert (
        datetime.fromisoformat(result.start_date.replace("Z", "+00:00"))
        == input.start_time
    )
    assert (
        datetime.fromisoformat(result.end_date.replace("Z", "+00:00")) == input.end_time
    )

    # Validate flag ranges
    for flag_count in result.flag_counts:
        assert 0 <= flag_count.flag <= 9  # Valid FEWS flags
        assert 0 <= flag_count.percentage <= 100

    # Print summary for manual verification
    print(f"\n=== FEWS Flag Analysis Results: {location_id} - {parameter_id} ===")
    print(f"\nAnalysis Period: {result.start_date} to {result.end_date}")
    print(f"Total Values: {result.total_values}")
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
        flag_def = result.flag_definitions[flag_count.flag]
        print(
            f"Flag {flag_count.flag:1d} ({flag_def.origin:>9s}, {flag_def.quality:>10s}): "
            f"{flag_count.count:3d} values ({flag_count.percentage:5.1f}%)"
        )
        print(f"   Description: {flag_def.description}")


@pytest.mark.asyncio
async def test_analyze_series_flags_invalid_time_range(test_context):
    """Test handling of invalid time ranges"""
    # Test end time before start time
    input = SeriesFlagsInput(
        location_id="KNMIUUR278",
        parameter_id="Eref.d",
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
        start_time=datetime.now(timezone.utc),
        end_time=future,
    )

    with pytest.raises(InvalidTimeRangeError) as exc:
        await analyze_series_flags(test_context, input)
    assert "future" in str(exc.value)


@fews_parallel("actueelwaterbeeld", "wsvv")
def test_analyze_series_flags_datetime_comparison_error(service):
    """
    Test that reproduces the WSVV datetime comparison error.

    This test should:
    - PASS for actueelwaterbeeld (working service)
    - FAIL for wsvv with: "can't compare offset-naive and offset-aware datetimes"

    Issue: https://github.com/HKV-products-services/talk-with-fews/issues/76

    NOTE: This test currently passes for both services, suggesting the datetime
    error may have been fixed or occurs under different conditions. The test
    serves as a regression test to catch the error if it reappears.
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
        # WSVV: Use exact parameters from issue #76 (timezone-naive datetimes)
        location_id = "HL000141"
        parameter_id = "H.G"  # Original parameter from issue
        start_time = datetime(2024, 1, 1)  # No timezone - this might cause the error!
        end_time = datetime(2024, 1, 14)  # No timezone - this might cause the error!
        print(
            f"Testing WSVV with original issue parameters: {location_id}/{parameter_id}"
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

    # Create test input
    input_data = SeriesFlagsInput(
        location_id=location_id,
        parameter_id=parameter_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Create context
    ctx = get_runtime_ctx(user_settings)

    try:
        # This should work for both services now (error may have been fixed)
        result = asyncio.run(analyze_series_flags(ctx, input_data))

        # If we get here, the test passed
        assert result is not None
        print(f"{service} test passed - {result.total_values} values found")

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
