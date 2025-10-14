"""
Get series headers with incremental caching from FEWS webservice.

This tool retrieves series headers using an incremental caching approach. It first checks
the local DuckDB cache, and if data is not found, it triggers ingestion from the webservice.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from talk_with_fews.utils.utils import format_datetime
import xml.etree.ElementTree as ET
import json

from pydantic_ai import RunContext, ModelRetry
from talk_with_fews.models.base import Deps
from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.utils.webservice_utils import get_request


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


def generate_time_step_description(
    time_step_unit: Optional[str], time_step_multiplier: Optional[int]
) -> Optional[str]:
    """
    Generate a combined time step description from unit and multiplier.

    Returns:
        Human-readable time step description or None
    """
    if not time_step_unit:
        return None

    if time_step_unit == "nonequidistant":
        return "Irregular time intervals (nonequidistant)"
    elif time_step_unit == "second" and time_step_multiplier:
        if time_step_multiplier == 86400:
            return "Daily data"
        elif time_step_multiplier == 3600:
            return "Hourly data"
        elif time_step_multiplier == 60:
            return "Minute data"
        else:
            return f"Data every {time_step_multiplier} seconds"
    elif time_step_unit == "day" and time_step_multiplier:
        if time_step_multiplier == 1:
            return "Daily data"
        else:
            return f"Data every {time_step_multiplier} days"
    elif time_step_unit == "hour" and time_step_multiplier:
        if time_step_multiplier == 1:
            return "Hourly data"
        else:
            return f"Data every {time_step_multiplier} hours"
    elif time_step_unit == "minute" and time_step_multiplier:
        if time_step_multiplier == 1:
            return "Minute data"
        else:
            return f"Data every {time_step_multiplier} minutes"
    else:
        return f"Data every {time_step_multiplier or 'unknown'} {time_step_unit}s"


def estimate_data_points_in_range(
    start_time: datetime,
    end_time: datetime,
    time_step_unit: Optional[str],
    time_step_multiplier: Optional[int],
) -> Optional[int]:
    """
    Estimate the number of data points in the requested time range.

    Returns:
        Estimated number of data points or None if cannot estimate
    """
    if not time_step_unit or time_step_unit == "nonequidistant":
        return None

    if not time_step_multiplier:
        return None

    # Calculate time span in seconds
    time_span_seconds = (end_time - start_time).total_seconds()

    # Calculate interval in seconds
    if time_step_unit == "second":
        interval_seconds = time_step_multiplier
    elif time_step_unit == "minute":
        interval_seconds = time_step_multiplier * 60
    elif time_step_unit == "hour":
        interval_seconds = time_step_multiplier * 3600
    elif time_step_unit == "day":
        interval_seconds = time_step_multiplier * 86400
    else:
        return None

    # Estimate data points
    estimated_points = int(time_span_seconds / interval_seconds) + 1
    return max(0, estimated_points)


@log_tool_call
async def get_series_statistics(
    ctx: RunContext[Deps], input: GetSeriesStatisticsInput
) -> GetSeriesStatisticsOutput:
    """
    Retrieve series statistics from FEWS webservice.

    Args:
        ctx: RunContext with database connection
        input: GetSeriesHeadersInput containing parameter_id AND location_id

    Returns:
        GetSeriesStatisticsOutput with series headers summary and follow-up suggestions
    """

    # Validate input
    if not input.parameter_id or not input.location_id:
        logger.error(
            "Both parameter_id and location_id must be provided for series statistics."
        )
        raise ModelRetry("Both parameter_id and location_id are required")  # noqa: F821

    webservice_url = ctx.deps.webservice_url
    location_id = input.location_id
    parameter_id = input.parameter_id

    request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
    params = {
        "locationIds": location_id,
        "parameterIds": parameter_id,
        "startTime": format_datetime(input.start_time),
        "endTime": format_datetime(input.end_time),
        "onlyHeaders": "True",
        "showStatistics": "true",
        "documentFormat": "PI_XML",
    }

    # Fetch data from webservice
    error, xml_content = get_request(request_url, params=params)  # noqa: F821
    if error is not None:
        # Check if it's a "No timeSeries found" error
        if "No timeSeries found" in error:
            return GetSeriesStatisticsOutput(
                description=f"No data found for parameter '{parameter_id}' and location '{location_id}'. This location-parameter combination has never had any data in this FEWS service."
            )
        else:
            return GetSeriesStatisticsOutput(
                description=f"Error fetching data: {error}"
            )

    namespace = {"pi": "http://www.wldelft.nl/fews/PI"}

    # Parse the XML response
    root = ET.fromstring(xml_content)

    # Locate the series element (should be one per parameter_id or location_id)
    series_elem = root.find(".//pi:series", namespace)
    if series_elem is None:
        return GetSeriesStatisticsOutput(
            description="No series element found in the response XML. The FEWS service returned an unexpected response format."
        )

    # Extract the header element containing metadata
    header_elem = series_elem.find("pi:header", namespace)
    if header_elem is None:
        return GetSeriesStatisticsOutput(
            description="Missing series header information. The FEWS service returned incomplete series information."
        )

    # Extract valueCount information
    count_elem = header_elem.find("pi:valueCount", namespace)
    count = int(count_elem.text) if count_elem is not None else 0

    # Extract time step information
    time_step_elem = header_elem.find("pi:timeStep", namespace)
    time_step_unit = time_step_elem.get("unit") if time_step_elem is not None else None
    time_step_multiplier = None
    if time_step_elem is not None and time_step_elem.get("multiplier"):
        try:
            time_step_multiplier = int(time_step_elem.get("multiplier"))
        except (ValueError, TypeError):
            time_step_multiplier = None

    # Extract parameter units
    units_elem = header_elem.find("pi:units", namespace)
    parameter_units = units_elem.text if units_elem is not None else None

    # Extract first and last value times for comparison
    first_value_elem = header_elem.find("pi:firstValueTime", namespace)
    last_value_elem = header_elem.find("pi:lastValueTime", namespace)

    if first_value_elem is not None and last_value_elem is not None:
        first_date = first_value_elem.get("date")
        first_time = first_value_elem.get("time")
        last_date = last_value_elem.get("date")
        last_time = last_value_elem.get("time")

        # Convert to datetime objects
        first_datetime = datetime.strptime(
            f"{first_date} {first_time}", "%Y-%m-%d %H:%M:%S"
        )
        last_datetime = datetime.strptime(
            f"{last_date} {last_time}", "%Y-%m-%d %H:%M:%S"
        )

        # Apply timezone
        timezone_offset = float(root.find("pi:timeZone", namespace).text)
        tz = timezone(timedelta(hours=timezone_offset))
        if timezone_offset != 0:
            first_datetime = first_datetime.replace(tzinfo=tz).astimezone(timezone.utc)
            last_datetime = last_datetime.replace(tzinfo=tz).astimezone(timezone.utc)
        else:
            first_datetime = first_datetime.replace(tzinfo=timezone.utc)
            last_datetime = last_datetime.replace(tzinfo=timezone.utc)

        # Check if the requested time range overlaps with available data
        requested_start = input.start_time
        requested_end = input.end_time

        # Convert to UTC for comparison
        if requested_start.tzinfo is None:
            requested_start = requested_start.replace(tzinfo=timezone.utc)
        else:
            requested_start = requested_start.astimezone(timezone.utc)

        if requested_end.tzinfo is None:
            requested_end = requested_end.replace(tzinfo=timezone.utc)
        else:
            requested_end = requested_end.astimezone(timezone.utc)

        # Check for time range overlap
        has_overlap = (
            requested_start <= last_datetime and requested_end >= first_datetime
        )

        if count == 0:
            return GetSeriesStatisticsOutput(
                description=f"No data found for parameter '{parameter_id}' and location '{location_id}'. This combination has no data available."
            )
        elif not has_overlap:
            # Data exists but not in the requested time range
            suggested_range = f"{first_datetime.strftime('%Y-%m-%d')} to {last_datetime.strftime('%Y-%m-%d')}"
            return GetSeriesStatisticsOutput(
                count=count,
                description=f"Data exists for parameter '{parameter_id}' and location '{location_id}' but not in the requested time range. Available data: {suggested_range}. Requested: {requested_start.strftime('%Y-%m-%d')} to {requested_end.strftime('%Y-%m-%d')}",
                first_value_time=first_datetime,
                last_value_time=last_datetime,
            )
        else:
            # Data exists and overlaps with requested time range
            # Extract minValue and maxValue
            min_value_elem = header_elem.find("pi:minValue", namespace)
            max_value_elem = header_elem.find("pi:maxValue", namespace)
            min_value = min_value_elem.text if min_value_elem is not None else None
            max_value = max_value_elem.text if max_value_elem is not None else None

            # Get interval analysis if requested and data exists
            interval_analysis = None

            if input.include_interval_analysis and count > 0:
                interval_analysis = await get_interval_statistics(
                    webservice_url,
                    location_id,
                    parameter_id,
                    input.start_time,
                    input.end_time,
                    input.interval_type,
                )

            # Estimate data points in requested range
            estimated_data_points = estimate_data_points_in_range(
                input.start_time, input.end_time, time_step_unit, time_step_multiplier
            )

            # Generate time step description
            time_step_description = generate_time_step_description(
                time_step_unit, time_step_multiplier
            )

            # Generate actionable description
            description = generate_actionable_description(
                count,
                parameter_id,
                location_id,
                min_value,
                max_value,
                first_datetime,
                last_datetime,
                time_step_description,
                parameter_units,
                interval_analysis,
                input.interval_type,
            )

            return GetSeriesStatisticsOutput(
                description=description,
                min_value=min_value,
                max_value=max_value,
                first_value_time=first_datetime,
                last_value_time=last_datetime,
                interval_analysis=interval_analysis,
                time_step=time_step_description,
                parameter_units=parameter_units,
                estimated_data_points_in_range=estimated_data_points,
            )
    else:
        # Fallback if we can't determine time ranges
        if count == 0:
            return GetSeriesStatisticsOutput(
                description=f"No data found for parameter '{parameter_id}' and location '{location_id}'. This combination has no data available."
            )
        else:
            # Extract minValue and maxValue
            min_value_elem = header_elem.find("pi:minValue", namespace)
            max_value_elem = header_elem.find("pi:maxValue", namespace)
            min_value = min_value_elem.text if min_value_elem is not None else None
            max_value = max_value_elem.text if max_value_elem is not None else None

            # Get interval analysis if requested and data exists
            interval_analysis = None

            if input.include_interval_analysis and count > 0:
                interval_analysis = await get_interval_statistics(
                    webservice_url,
                    location_id,
                    parameter_id,
                    input.start_time,
                    input.end_time,
                    input.interval_type,
                )

            # Estimate data points in requested range
            estimated_data_points = estimate_data_points_in_range(
                input.start_time, input.end_time, time_step_unit, time_step_multiplier
            )

            # Generate time step description
            time_step_description = generate_time_step_description(
                time_step_unit, time_step_multiplier
            )

            # Generate actionable description
            description = generate_actionable_description(
                count,
                parameter_id,
                location_id,
                min_value,
                max_value,
                input.start_time,
                input.end_time,
                time_step_description,
                parameter_units,
                interval_analysis,
                input.interval_type,
            )

            return GetSeriesStatisticsOutput(
                description=description,
                min_value=min_value,
                max_value=max_value,
                interval_analysis=interval_analysis,
                time_step=time_step_description,
                parameter_units=parameter_units,
                estimated_data_points_in_range=estimated_data_points,
            )
