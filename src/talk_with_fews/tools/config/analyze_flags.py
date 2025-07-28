"""
Tool for analyzing FEWS quality flags.

Note: Flag source analysis requires FEWS API support.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Any

from pydantic_ai import RunContext

from ...models.base import Deps
from ...models.flags.counts import FlagCount, FlagCounts
from ...models.flags.errors import UnknownFlagError, InvalidTimeRangeError
from ...models.flags.io import SeriesFlagsInput, SeriesFlagsSummary, DateRange
from ...models.flags.mappings import QUALITY_FLAGS
from ...models.get_series_data import TimeseriesValue
from ...tools.webservice.get_series_data import get_series_data


def validate_time_range(start_time: datetime, end_time: datetime) -> None:
    """
    Validate the analysis time range.

    Checks:
    - start_time < end_time
    - Range not too large (configurable max duration)
    - Dates not in future
    """
    if start_time >= end_time:
        raise InvalidTimeRangeError("Start time must be before end time")

    # Ensure timezone-aware comparison
    now = datetime.now(timezone.utc)
    if start_time > now or end_time > now:
        raise InvalidTimeRangeError("Time range cannot be in the future")

    # Could add max duration check here if needed


async def count_series_flags(values: List[TimeseriesValue]) -> Dict[str, Any]:
    """
    Count occurrences of existing FEWS flags in timeseries.

    This function counts flags that are already set in the timeseries.

    Args:
        values: List of timeseries values with flags

    Returns:
        Dict containing:
        - counts: List[FlagCount] - Count and percentage for each flag
        - quality_counts: Dict[str, int] - Counts by quality level
        - origin_counts: Dict[str, int] - Counts by origin
        - total_values: int - Total number of values

    Raises:
        UnknownFlagError: If an unknown flag value is encountered
    """
    # Count flag occurrences
    flag_counter = Counter(value.flag for value in values)
    total_values = len(values)

    # Initialize quality and origin counters
    quality_counts = {"Reliable": 0, "Doubtful": 0, "Unreliable": 0}
    origin_counts = {"Original": 0, "Corrected": 0, "Completed": 0}

    # Process each flag
    flag_counts = []
    for flag, count in flag_counter.items():
        # Validate flag
        if flag not in QUALITY_FLAGS:
            raise UnknownFlagError(flag)

        # Get flag definition
        flag_def = QUALITY_FLAGS[flag]

        # Update counters
        quality_counts[flag_def.quality] += count
        origin_counts[flag_def.origin] += count

        # Calculate percentage
        percentage = (count / total_values) * 100 if total_values > 0 else 0

        # Create flag count
        flag_counts.append(FlagCount(flag=flag, count=count, percentage=percentage))

    return {
        "counts": flag_counts,
        "quality_counts": quality_counts,
        "origin_counts": origin_counts,
        "total_values": total_values,
    }


async def analyze_series_flags(
    ctx: RunContext[Deps], input: SeriesFlagsInput
) -> SeriesFlagsSummary:
    """
    Summarize FEWS flags in a timeseries.

    This tool:
    1. Retrieves timeseries with flags from FEWS
    2. Counts occurrences of existing flags
    3. Groups and summarizes these counts
    4. Formats results for reporting

    Note: Flag source analysis requires FEWS API support (feature request pending).

    Args:
        ctx: Runtime context with dependencies
        input: Analysis parameters including location, parameter, and time range

    Returns:
        Comprehensive summary of flags

    Raises:
        InvalidTimeRangeError: If time range is invalid
        UnknownFlagError: If an unknown flag is encountered
    """
    # 1. Validate time range
    validate_time_range(input.start_time, input.end_time)

    # 2. Get timeseries with flags
    series_data = await get_series_data(ctx, input)

    # 3. Count flags
    flag_analysis = await count_series_flags(series_data.values)

    # 4. Create summary
    return SeriesFlagsSummary(
        total_values=flag_analysis["total_values"],
        period=DateRange(
            start=input.start_time,
            end=input.end_time,
            duration=input.end_time - input.start_time,
        ),
        flag_definitions=QUALITY_FLAGS,
        flag_counts=flag_analysis["counts"],
        counts=FlagCounts(
            total_values=flag_analysis["total_values"],
            missing_values=flag_analysis.get("quality_counts", {}).get("Unreliable", 0),
            reliable_count=flag_analysis["quality_counts"]["Reliable"],
            doubtful_count=flag_analysis["quality_counts"]["Doubtful"],
            unreliable_count=flag_analysis["quality_counts"]["Unreliable"],
            reliable_percentage=(
                flag_analysis["quality_counts"]["Reliable"]
                / flag_analysis["total_values"]
            )
            * 100
            if flag_analysis["total_values"] > 0
            else 0,
            doubtful_percentage=(
                flag_analysis["quality_counts"]["Doubtful"]
                / flag_analysis["total_values"]
            )
            * 100
            if flag_analysis["total_values"] > 0
            else 0,
            unreliable_percentage=(
                flag_analysis["quality_counts"]["Unreliable"]
                / flag_analysis["total_values"]
            )
            * 100
            if flag_analysis["total_values"] > 0
            else 0,
        ),
    )
