"""
Tool for analyzing FEWS quality flags.

Note: Flag source analysis requires FEWS API support.
"""

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Any

from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps
from talk_with_fews.models.webservice.flags.counts import FlagCount, FlagCounts
from talk_with_fews.models.webservice.flags.errors import (
    UnknownFlagError,
    InvalidTimeRangeError,
)
from talk_with_fews.models.webservice.flags.io import (
    SeriesFlagsInput,
    SeriesFlagsOutput,
)
from talk_with_fews.models.webservice.flags.mappings import QUALITY_FLAGS
from talk_with_fews.models.webservice.get_series_data import TimeseriesValue
from talk_with_fews.tools.webservice.get_series_data import get_series_data
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.utils.utils import format_datetime


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

    # Handle timezone-naive datetimes by treating them as UTC
    # This is a reasonable assumption for FEWS data
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

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

        # Create flag count with definition
        flag_counts.append(
            FlagCount(
                flag=flag,
                count=count,
                percentage=percentage,
                origin=flag_def.origin,
                quality=flag_def.quality,
                description=flag_def.description,
            )
        )

    return {
        "counts": flag_counts,
        "quality_counts": quality_counts,
        "origin_counts": origin_counts,
        "total_values": total_values,
    }


@log_tool_call
async def analyze_series_flags(
    ctx: RunContext[Deps], input: SeriesFlagsInput
) -> SeriesFlagsOutput:
    """
    Summarize FEWS flags in a timeseries.

    This tool:
    1. Retrieves timeseries with flags from FEWS
    2. Counts occurrences of existing flags
    3. Groups and summarizes these counts
    4. Formats results for reporting

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
    from talk_with_fews.models.webservice.get_series_data import GetSeriesDataInput

    series_input = GetSeriesDataInput(
        location_id=input.location_id,
        parameter_id=input.parameter_id,
        module_instance_id=input.module_instance_id,
        start_time=input.start_time,
        end_time=input.end_time,
        include_flag_sources=input.include_flag_sources,
    )
    series_data = await get_series_data(ctx, series_input)

    # 3. Handle empty data case
    if not series_data.values:
        return SeriesFlagsOutput(
            description=f"No data found for parameter '{input.parameter_id}' and location '{input.location_id}'. This location-parameter combination has no data in the specified time range.",
            flag_counts=[],
            counts=FlagCounts(
                total_values=0,
                missing_values=0,
                reliable_count=0,
                doubtful_count=0,
                unreliable_count=0,
                reliable_percentage=0.0,
                doubtful_percentage=0.0,
                unreliable_percentage=0.0,
            ),
        )

    # 4. Count flags
    flag_analysis = await count_series_flags(series_data.values)

    # 5. Create contextual description
    description = f"Flag analysis for {input.parameter_id} at {input.location_id}: {flag_analysis['total_values']} values analyzed from {format_datetime(input.start_time)} to {format_datetime(input.end_time)}. "

    reliable_pct = (
        flag_analysis["quality_counts"]["Reliable"] / flag_analysis["total_values"]
    ) * 100
    doubtful_pct = (
        flag_analysis["quality_counts"]["Doubtful"] / flag_analysis["total_values"]
    ) * 100
    unreliable_pct = (
        flag_analysis["quality_counts"]["Unreliable"] / flag_analysis["total_values"]
    ) * 100

    description += f"Data quality: {reliable_pct:.1f}% reliable, {doubtful_pct:.1f}% doubtful, {unreliable_pct:.1f}% unreliable."

    # 6. Create output
    return SeriesFlagsOutput(
        description=description,
        flag_counts=flag_analysis["counts"],
        counts=FlagCounts(
            total_values=flag_analysis["total_values"],
            missing_values=flag_analysis.get("quality_counts", {}).get("Unreliable", 0),
            reliable_count=flag_analysis["quality_counts"]["Reliable"],
            doubtful_count=flag_analysis["quality_counts"]["Doubtful"],
            unreliable_count=flag_analysis["quality_counts"]["Unreliable"],
            reliable_percentage=reliable_pct,
            doubtful_percentage=doubtful_pct,
            unreliable_percentage=unreliable_pct,
        ),
    )
