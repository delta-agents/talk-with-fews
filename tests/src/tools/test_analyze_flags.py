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
