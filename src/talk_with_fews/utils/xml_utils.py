"""
XML parsing utilities for FEWS webservice responses.

This module provides reusable functions for parsing FEWS TimeSeries PI-XML responses,
including statistics parsing and data extraction that can be used across multiple tools.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable

from talk_with_fews.models.webservice.get_series_statistics import (
    SeriesStatisticsItem,
)
from talk_with_fews.utils.logging_utils import logger


def generate_time_step_description(
    time_step_unit: Optional[str], time_step_multiplier: Optional[int]
) -> Optional[str]:
    """
    Generate a human-readable description of the time step.

    Args:
        time_step_unit: Time step unit (e.g., 'second', 'minute', 'hour', 'day')
        time_step_multiplier: Time step multiplier

    Returns:
        Human-readable time step description or None
    """
    if not time_step_unit or time_step_multiplier is None:
        return None

    if time_step_unit == "nonequidistant":
        return "Irregular time intervals (nonequidistant)"

    # Convert to a more readable format
    if time_step_unit == "second":
        if time_step_multiplier == 1:
            return "Data every second"
        elif time_step_multiplier == 60:
            return "Minute data"
        elif time_step_multiplier == 3600:
            return "Hourly data"
        elif time_step_multiplier == 86400:
            return "Daily data"
        else:
            return f"Data every {time_step_multiplier} seconds"
    elif time_step_unit == "minute":
        if time_step_multiplier == 1:
            return "Minute data"
        elif time_step_multiplier == 60:
            return "Hourly data"
        elif time_step_multiplier == 1440:
            return "Daily data"
        else:
            return f"Data every {time_step_multiplier} minutes"
    elif time_step_unit == "hour":
        if time_step_multiplier == 1:
            return "Hourly data"
        elif time_step_multiplier == 24:
            return "Daily data"
        else:
            return f"Data every {time_step_multiplier} hours"
    elif time_step_unit == "day":
        if time_step_multiplier == 1:
            return "Daily data"
        else:
            return f"Data every {time_step_multiplier} days"
    else:
        return f"Data every {time_step_multiplier} {time_step_unit}"


def estimate_data_points_in_range(
    start_time: datetime,
    end_time: datetime,
    time_step_unit: Optional[str],
    time_step_multiplier: Optional[int],
) -> Optional[int]:
    """
    Estimate the number of data points in a time range based on time step information.

    Args:
        start_time: Start of the time range
        end_time: End of the time range
        time_step_unit: Time step unit (e.g., 'second', 'minute', 'hour', 'day')
        time_step_multiplier: Time step multiplier

    Returns:
        Estimated number of data points or None if cannot be calculated
    """
    if (
        not time_step_unit
        or time_step_multiplier is None
        or time_step_unit == "nonequidistant"
    ):
        return None

    # Calculate time span in seconds
    time_span = end_time - start_time
    time_span_seconds = time_span.total_seconds()

    # Convert time step to seconds
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


async def parse_timeseries_xml_statistics(
    xml_content: str,
    start_time: datetime,
    end_time: datetime,
    include_interval_analysis: bool = False,
    interval_type: str = "MONTH",
    webservice_url: Optional[str] = None,
    get_interval_statistics_func: Optional[Callable] = None,
) -> list[SeriesStatisticsItem]:
    """
    Parse FEWS TimeSeries PI-XML and extract statistics for all series.

    This function handles multiple series in a single XML response and returns
    comprehensive statistics for each series, including identification of the
    primary series for thinning calculations.

    Args:
        xml_content: Raw XML content from FEWS webservice
        start_time: Start time for analysis
        end_time: End time for analysis
        include_interval_analysis: Whether to include interval analysis
        interval_type: Type of interval analysis (e.g., "MONTH", "CALENDAR_DAY")
        webservice_url: URL of the webservice (required if include_interval_analysis=True)
        get_interval_statistics_func: Function to call for interval statistics (required if include_interval_analysis=True)

    Returns:
        List of SeriesStatisticsItem objects, one for each series
    """
    namespace = {"pi": "http://www.wldelft.nl/fews/PI"}

    # Parse the XML response
    root = ET.fromstring(xml_content)

    # Locate all series elements
    series_elements = root.findall(".//pi:series", namespace)
    if not series_elements:
        # Return empty list
        return []

    # Process each series
    all_series_stats = []
    primary_series_index = None

    for series_idx, series_elem in enumerate(series_elements):
        try:
            # Extract header information
            header_elem = series_elem.find("pi:header", namespace)
            if header_elem is None:
                logger.warning(f"Series {series_idx} missing header, skipping")
                continue

            # Extract basic metadata
            module_instance_id = header_elem.find("pi:moduleInstanceId", namespace)
            module_instance_id = (
                module_instance_id.text if module_instance_id is not None else None
            )

            # Extract location and parameter IDs from the header
            location_id_elem = header_elem.find("pi:locationId", namespace)
            location_id = (
                location_id_elem.text if location_id_elem is not None else None
            )

            parameter_id_elem = header_elem.find("pi:parameterId", namespace)
            parameter_id = (
                parameter_id_elem.text if parameter_id_elem is not None else None
            )

            # Extract valueCount
            count_elem = header_elem.find("pi:valueCount", namespace)
            count = int(count_elem.text) if count_elem is not None else 0

            # Extract time step information
            time_step_elem = header_elem.find("pi:timeStep", namespace)
            time_step_unit = (
                time_step_elem.get("unit") if time_step_elem is not None else None
            )
            time_step_multiplier = None
            if time_step_elem is not None and time_step_elem.get("multiplier"):
                try:
                    time_step_multiplier = int(time_step_elem.get("multiplier"))
                except (ValueError, TypeError):
                    time_step_multiplier = None

            # Extract parameter units
            units_elem = header_elem.find("pi:units", namespace)
            parameter_units = units_elem.text if units_elem is not None else None

            # Extract time range information
            first_value_elem = header_elem.find("pi:firstValueTime", namespace)
            last_value_elem = header_elem.find("pi:lastValueTime", namespace)

            first_datetime = None
            last_datetime = None

            if first_value_elem is not None and last_value_elem is not None:
                first_date = first_value_elem.get("date")
                first_time = first_value_elem.get("time")
                last_date = last_value_elem.get("date")
                last_time = last_value_elem.get("time")

                if first_date and first_time and last_date and last_time:
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
                        first_datetime = first_datetime.replace(tzinfo=tz).astimezone(
                            timezone.utc
                        )
                        last_datetime = last_datetime.replace(tzinfo=tz).astimezone(
                            timezone.utc
                        )
                    else:
                        first_datetime = first_datetime.replace(tzinfo=timezone.utc)
                        last_datetime = last_datetime.replace(tzinfo=timezone.utc)

            # Extract min/max values
            min_value_elem = header_elem.find("pi:minValue", namespace)
            max_value_elem = header_elem.find("pi:maxValue", namespace)
            min_value = min_value_elem.text if min_value_elem is not None else None
            max_value = max_value_elem.text if max_value_elem is not None else None

            # Generate time step description
            time_step_description = generate_time_step_description(
                time_step_unit, time_step_multiplier
            )

            # Create timestep_info
            timestep_info = None
            if time_step_unit and time_step_multiplier:
                timestep_info = {
                    "unit": time_step_unit,
                    "multiplier": time_step_multiplier,
                }

            # Estimate data points in requested range
            estimated_data_points = estimate_data_points_in_range(
                start_time, end_time, time_step_unit, time_step_multiplier
            )

            # If timestep is nonequidistant, be conservative and set to 1000
            if time_step_unit == "nonequidistant" or estimated_data_points is None:
                estimated_data_points = 1000

            # Generate description for this series
            description_parts = []

            # Add location and parameter identification with abbreviations
            id_parts = []
            if location_id:
                id_parts.append(f"loc: {location_id}")
            if parameter_id:
                id_parts.append(f"par: {parameter_id}")
            if module_instance_id:
                id_parts.append(f"module: {module_instance_id}")

            if id_parts:
                description_parts.append(", ".join(id_parts))

            # Add value count
            description_parts.append(f"{count} values")
            if time_step_description:
                description_parts.append(time_step_description)
            if parameter_units:
                description_parts.append(f"Units: {parameter_units}")
            if min_value is not None and max_value is not None:
                description_parts.append(f"Range: {min_value} to {max_value}")

            series_description = ". ".join(description_parts) + "."

            # Fetch interval analysis if requested
            interval_analysis = None
            if include_interval_analysis and location_id and parameter_id:
                if webservice_url and get_interval_statistics_func:
                    try:
                        interval_analysis = await get_interval_statistics_func(
                            webservice_url=webservice_url,
                            location_id=location_id,
                            parameter_id=parameter_id,
                            start_time=start_time,
                            end_time=end_time,
                            interval_type=interval_type,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch interval statistics for {location_id}/{parameter_id}: {e}"
                        )
                        interval_analysis = None

            # Create the series statistics object
            series_stat = SeriesStatisticsItem(
                description=series_description,
                min_value=min_value,
                max_value=max_value,
                parameter_units=parameter_units,
                first_value_time=first_datetime,
                last_value_time=last_datetime,
                time_step=time_step_description,
                timestep_info=timestep_info,
                estimated_data_points_in_range=estimated_data_points,
                module_instance_id=module_instance_id,
                location_id=location_id,
                parameter_id=parameter_id,
                interval_analysis=interval_analysis,
            )

            all_series_stats.append(series_stat)

            # Identify primary series (prefer regular time steps over nonequidistant)
            if primary_series_index is None:
                if (
                    time_step_unit != "nonequidistant"
                    and time_step_multiplier is not None
                ):
                    primary_series_index = series_idx
            elif (
                time_step_unit != "nonequidistant" and time_step_multiplier is not None
            ):
                # If we already have a primary series, keep the first one found
                pass

        except Exception as e:
            logger.warning(f"Error processing series {series_idx}: {e}")
            continue

    # Return the list of series statistics
    return all_series_stats
