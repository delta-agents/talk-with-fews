"""
Get timeseries data from FEWS webservice for specific location-parameter combinations.

Note: Flag source retrieval requires FEWS API support (feature request pending).
"""

import xml.etree.ElementTree as ET
from typing import Tuple, List
from datetime import datetime, timezone, timedelta

import httpx
from pydantic_ai import RunContext

from talk_with_fews.models.webservice.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
    TimeseriesValue,
)
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.utils.utils import format_datetime


async def parse_timeseries_xml(xml_content: str) -> Tuple[dict, List[TimeseriesValue]]:
    """
    Parse FEWS XML response into metadata and timeseries values.
    Handles missing values internally based on the missVal from header.

    Note: Flag source parsing requires FEWS API support (feature request pending).

    Returns:
        Tuple[dict, List[TimeseriesValue]]: Metadata and list of values
    """
    root = ET.fromstring(xml_content)
    ns = {"pi": "http://www.wldelft.nl/fews/PI"}

    # Get timezone offset from XML
    timezone_offset = float(root.find("pi:timeZone", ns).text)
    tz = timezone(timedelta(hours=timezone_offset))

    # Parse header information
    header = root.find(".//pi:header", ns)
    missing_value = float(header.find("pi:missVal", ns).text)
    metadata = {
        "moduleinstance_id": header.find("pi:moduleInstanceId", ns).text,
        "location_id": header.find("pi:locationId", ns).text,
        "parameter_id": header.find("pi:parameterId", ns).text,
        "station_name": header.find("pi:stationName", ns).text,
        "units": header.find("pi:units", ns).text,
        "lat": float(header.find("pi:lat", ns).text),
        "lon": float(header.find("pi:lon", ns).text),
        "x": float(header.find("pi:x", ns).text),
        "y": float(header.find("pi:y", ns).text),
        "z": float(header.find("pi:z", ns).text)
        if header.find("pi:z", ns) is not None
        else None,
        "type": header.find("pi:type", ns).text,
    }

    # Parse events
    values = []
    for event in root.findall(".//pi:event", ns):
        date = event.get("date")
        time = event.get("time")
        value = float(event.get("value"))

        # Handle missing values: if value equals missing_value indicator, set to None
        value = None if value == missing_value else value

        # Combine date and time strings and parse into a datetime object with the XML-specified timezone
        event_datetime = datetime.fromisoformat(f"{date}T{time}")
        # Convert to UTC if not already UTC timezone
        if timezone_offset != 0:
            event_datetime = event_datetime.replace(tzinfo=tz).astimezone(timezone.utc)
        else:
            event_datetime = event_datetime.replace(tzinfo=timezone.utc)

        value_data = {
            "datetime": event_datetime,
            "value": value,
            "flag": int(event.get("flag")),
        }

        # Add flag source if present in XML (requires FEWS API support)
        flag_source = event.get("flagSource")
        if flag_source:
            value_data["flag_source"] = flag_source

        values.append(TimeseriesValue(**value_data))

    return metadata, values


@log_tool_call
async def get_series_data(
    ctx: RunContext[Deps], input: GetSeriesDataInput
) -> GetSeriesDataOutput:
    """
    Retrieve timeseries data for a specific location-parameter combination.

    Automatically applies thinning for large datasets (>500 estimated points) to ensure
    manageable data retrieval for AI assistants.


    Args:
        ctx: Runtime context with webservice URL
        input: GetSeriesDataInput containing location_id, parameter_id, and time range

    Returns:
        GetSeriesDataOutput containing optimized timeseries values (only changing data)
        and metadata (static information). AI assistants can generate CSV format if needed.
    """
    # Step 1: Check estimated data points using get_series_statistics
    from talk_with_fews.tools.webservice.get_series_statistics import (
        get_series_statistics,
    )
    from talk_with_fews.models.webservice.get_series_statistics import (
        GetSeriesStatisticsInput,
        IntervalType,
    )

    stats_input = GetSeriesStatisticsInput(
        location_id=input.location_id,
        parameter_id=input.parameter_id,
        module_instance_id=input.module_instance_id,
        start_time=input.start_time,
        end_time=input.end_time,
        include_interval_analysis=False,
        interval_type=IntervalType.MONTH,
    )

    stats_result = await get_series_statistics(ctx, stats_input)

    # Get estimated points from the series (should be only one since moduleInstanceId is specified)
    estimated_points = None
    if stats_result and stats_result.series_statistics:
        # Since moduleInstanceId is specified, we should get exactly one series
        estimated_points = stats_result.series_statistics[
            0
        ].estimated_data_points_in_range

    # Step 2: Determine if thinning is needed
    thinning_applied = False
    thinning_value = None
    thinning_reason = None

    # Primary check: Use estimated_points from get_series_statistics
    if estimated_points and estimated_points > 500:
        # Calculate thinning: view period in ms / display pixels
        # For 5 years on 1024 pixels: 157784760000 / 1024 = 15408668 ms/pixel
        time_span_ms = int((input.end_time - input.start_time).total_seconds() * 1000)
        display_pixels = 1024  # Standard display width
        thinning_value = time_span_ms // display_pixels
        thinning_applied = True
        thinning_reason = f"Automatic thinning applied for large dataset ({estimated_points:,} estimated points > 500)"

    # Step 3: Construct URL with moduleInstanceId and optional thinning parameter
    url = (
        f"{ctx.deps.webservice_url}/rest/fewspiservice/v1/timeseries"
        f"?locationIds={input.location_id}"
        f"&parameterIds={input.parameter_id}"
        f"&moduleInstanceIds={input.module_instance_id}"
        f"&startTime={format_datetime(input.start_time)}"
        f"&endTime={format_datetime(input.end_time)}"
        f"&documentFormat=PI_XML"
    )

    # Add thinning parameter if needed
    if thinning_applied:
        url += f"&thinning={thinning_value}"

    # Add flag source parameter if requested
    if input.include_flag_sources:
        url += "&includeFlagSources=true"

    # Fetch data from webservice
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            # Check if it's a "No timeSeries found" error
            if "No timeSeries found" in response.text:
                # Return empty data instead of raising an error
                return GetSeriesDataOutput(
                    values=[],
                    metadata={},
                )
            else:
                raise Exception(f"Failed to fetch data: {response.text}")
        xml_content = response.text

    # Parse response
    metadata, values = await parse_timeseries_xml(xml_content)

    # Add thinning information to metadata
    if thinning_applied:
        metadata["thinning_applied"] = True
        metadata["thinning_value"] = thinning_value
        metadata["estimated_original_points"] = estimated_points
        metadata["thinning_reason"] = thinning_reason

    return GetSeriesDataOutput(values=values, metadata=metadata)
