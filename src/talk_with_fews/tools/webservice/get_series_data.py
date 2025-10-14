"""
Get timeseries data from FEWS webservice for specific location-parameter combinations.

Note: Flag source retrieval requires FEWS API support (feature request pending).
"""

import xml.etree.ElementTree as ET
from typing import Tuple, List
from datetime import datetime, timezone, timedelta

import httpx
from pydantic_ai import RunContext

from talk_with_fews.models.get_series_data import (
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
            "location_id": metadata["location_id"],
            "station_name": metadata["station_name"],
            "parameter_id": metadata["parameter_id"],
            "moduleinstance_id": metadata["moduleinstance_id"],
            "value": value,
            "flag": int(event.get("flag")),
        }

        # Add flag source if present in XML (requires FEWS API support)
        flag_source = event.get("flagSource")
        if flag_source:
            value_data["flag_source"] = flag_source

        values.append(TimeseriesValue(**value_data))

    return metadata, values


def convert_to_csv(values: List[TimeseriesValue]) -> str:
    """
    Convert timeseries values to CSV format.
    Only includes flag_source column if any value has a flag source.
    """
    # Base headers without flag_source
    headers = [
        "datetime",
        "location_id",
        "station_name",
        "parameter_id",
        "moduleinstance_id",
        "value",
        "flag",
    ]

    # Check if any value has a flag_source
    if any(value.flag_source is not None for value in values):
        headers.append("flag_source")

    # Create CSV string manually to ensure consistent line endings
    lines = [",".join(headers)]
    for value in values:
        data = value.model_dump()
        lines.append(
            ",".join("" if data.get(h) is None else str(data[h]) for h in headers)
        )

    return "\n".join(lines)


@log_tool_call
async def get_series_data(
    ctx: RunContext[Deps], input: GetSeriesDataInput
) -> GetSeriesDataOutput:
    """
    Retrieve timeseries data for a specific location-parameter combination.

    Note: Flag source retrieval requires FEWS API support (feature request pending).

    Args:
        ctx: Runtime context with webservice URL
        input: GetSeriesDataInput containing location_id, parameter_id, and time range

    Returns:
        GetSeriesDataOutput containing the timeseries values, metadata, and CSV formatted data
    """
    # Construct URL with proper datetime format
    url = (
        f"{ctx.deps.webservice_url}/rest/fewspiservice/v1/timeseries"
        f"?locationIds={input.location_id}"
        f"&parameterIds={input.parameter_id}"
        f"&startTime={format_datetime(input.start_time)}"
        f"&endTime={format_datetime(input.end_time)}"
        f"&documentFormat=PI_XML"
    )

    # Add flag source parameter if requested (requires FEWS API support)
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
                    csv_data="datetime,location_id,station_name,parameter_id,moduleinstance_id,value,flag",
                )
            else:
                raise Exception(f"Failed to fetch data: {response.text}")
        xml_content = response.text

    # Parse response and convert to CSV
    metadata, values = await parse_timeseries_xml(xml_content)
    csv_data = convert_to_csv(values)

    return GetSeriesDataOutput(values=values, metadata=metadata, csv_data=csv_data)
