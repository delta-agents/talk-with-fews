"""
Get series headers with incremental caching from FEWS webservice.

This tool retrieves series headers using an incremental caching approach. It first checks
the local DuckDB cache, and if data is not found, it triggers ingestion from the webservice.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from talk_with_fews.utils.utils import format_datetime
import json

from pydantic_ai import RunContext, ModelRetry
from talk_with_fews.models.base import Deps
from talk_with_fews.models.webservice.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.utils.webservice_utils import get_request
from talk_with_fews.utils.xml_utils import parse_timeseries_xml_statistics


async def get_interval_statistics(
    webservice_url: str,
    location_id: str,
    parameter_id: str,
    start_time: datetime,
    end_time: datetime,
    interval_type: str,
) -> Dict[str, Any]:
    """
    Get interval statistics from FEWS webservice.

    Returns:
        Dictionary containing interval analysis results or None if not available
    """
    try:
        request_url = (
            f"{webservice_url}/rest/fewspiservice/v1/timeseries/intervalstatistics"
        )
        # Try English statistics first, fall back to Dutch if needed
        statistics_to_try = [
            "count_numberOfValues,percentage_reliable",  # English
            "aantal waarden,% betrouwbaar",  # Dutch
        ]

        error = None
        json_content = None

        for statistics in statistics_to_try:
            params = {
                "locationIds": location_id,
                "parameterIds": parameter_id,
                "startTime": format_datetime(start_time),
                "endTime": format_datetime(end_time),
                "interval": interval_type,
                "statistics": statistics,
                "documentFormat": "PI_JSON",
            }

            error, json_content = get_request(request_url, params=params)
            if error is None:
                break
            elif "Invalid statistic" in error:
                continue  # Try next statistics format
            else:
                break  # Other error, stop trying

        if error is not None:
            logger.warning(f"Interval statistics not available: {error}")
            return None

        data = json.loads(json_content)
        time_series_stats = data.get("timeSeriesIntervalStatistics", [])

        if not time_series_stats:
            return None

        # Extract the first series statistics
        series_stats = time_series_stats[0]
        interval_stats = series_stats.get("intervalstatistics", [])

        if not interval_stats:
            return None

        # Process the interval statistics
        result = {"interval_type": interval_type, "statistics": []}

        for stat in interval_stats:
            stat_name = stat.get("statistic", "unknown")
            values = stat.get("values", [[]])[
                0
            ]  # Get first (and usually only) value array

            # Convert values to a more readable format
            processed_values = {}
            for value_obj in values:
                for date_key, value in value_obj.items():
                    processed_values[date_key] = value

            result["statistics"].append({"name": stat_name, "values": processed_values})

        return result

    except Exception as e:
        logger.warning(f"Failed to get interval statistics: {e}")
        return None


def generate_actionable_description(
    count: int,
    parameter_id: str,
    location_id: str,
    min_value: Optional[str],
    max_value: Optional[str],
    first_datetime: Optional[datetime],
    last_datetime: Optional[datetime],
    time_step_description: Optional[str],
    parameter_units: Optional[str],
    interval_analysis: Optional[Dict[str, Any]],
    interval_type: str,
) -> str:
    """
    Generate a clear, factual description without vague recommendations.

    Returns:
        String with factual information about the data
    """
    # Basic information
    parts = [
        f"Found {count} values for parameter '{parameter_id}' and location '{location_id}'"
    ]

    # Time range information
    if first_datetime and last_datetime:
        parts.append(
            f"Data available from {first_datetime.strftime('%Y-%m-%d')} to {last_datetime.strftime('%Y-%m-%d')}"
        )

    # Time step information
    if time_step_description:
        parts.append(time_step_description)

    # Parameter units
    if parameter_units:
        parts.append(f"Units: {parameter_units}")

    # Value range
    if min_value is not None and max_value is not None:
        if parameter_units:
            parts.append(f"Value range: {min_value} to {max_value} ({parameter_units})")
        else:
            parts.append(f"Value range: {min_value} to {max_value}")

    # Interval analysis status - only mention if actually available
    if interval_analysis:
        parts.append(f"Interval analysis available by {interval_type.lower()}")

    return ". ".join(parts) + "."


@log_tool_call
async def get_series_statistics(
    ctx: RunContext[Deps], input: GetSeriesStatisticsInput
) -> GetSeriesStatisticsOutput:
    """
    Retrieve series statistics from FEWS webservice.

    Requires a valid parameter_id + location_id combination that exists in the FEWS service.
    Use get_series_headers to find valid combinations before calling this function.

    Args:
        ctx: RunContext with database connection
        input: GetSeriesStatisticsInput containing parameter_id AND location_id

    Returns:
        GetSeriesStatisticsOutput wrapper containing list of series statistics
    """

    # Validate input
    if not input.parameter_id or not input.location_id:
        logger.error(
            "Both parameter_id and location_id must be provided for series statistics."
        )
        raise ModelRetry("Both parameter_id and location_id are required")  # noqa: F821

    webservice_url = ctx.deps.webservice_url

    # Convert lists to comma-separated strings for the API
    if isinstance(input.location_id, list):
        location_id = ",".join(input.location_id)
    else:
        location_id = input.location_id

    if isinstance(input.parameter_id, list):
        parameter_id = ",".join(input.parameter_id)
    else:
        parameter_id = input.parameter_id

    request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
    params = {
        "locationIds": location_id,  # Comma-separated string for API
        "parameterIds": parameter_id,  # Comma-separated string for API
        "startTime": format_datetime(input.start_time),
        "endTime": format_datetime(input.end_time),
        "onlyHeaders": "True",
        "showStatistics": "true",
        "documentFormat": "PI_XML",
    }

    # Add moduleInstanceId if provided
    if input.module_instance_id:
        params["moduleInstanceIds"] = input.module_instance_id

    # Fetch data from webservice
    error, xml_content = get_request(request_url, params=params)  # noqa: F821
    if error is not None:
        # Check if it's a "No timeSeries found" error
        if "No timeSeries found" in error:
            return GetSeriesStatisticsOutput(
                series_statistics=[],
                description="No time series found for the given parameters.",
            )
        else:
            # Return error result wrapped
            return GetSeriesStatisticsOutput(
                series_statistics=[], description=f"Error fetching data: {error}"
            )

    # Parse the XML using the new parsing function
    # Note: location_id and parameter_id are extracted from each series element in the XML,
    # so we don't need to pass them as parameters
    series_statistics = await parse_timeseries_xml_statistics(
        xml_content=xml_content,
        start_time=input.start_time,
        end_time=input.end_time,
        include_interval_analysis=input.include_interval_analysis,
        interval_type=input.interval_type.value,
        webservice_url=webservice_url if input.include_interval_analysis else None,
        get_interval_statistics_func=get_interval_statistics
        if input.include_interval_analysis
        else None,
    )

    # Generate a summary description
    num_series = len(series_statistics)
    if num_series == 0:
        description = "No statistics found for the given parameters."
    elif num_series == 1:
        description = "Statistics for 1 series available."
    else:
        description = f"Statistics for {num_series} series available."

    return GetSeriesStatisticsOutput(
        series_statistics=series_statistics, description=description
    )
