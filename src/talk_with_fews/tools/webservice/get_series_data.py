"""
Get timeseries data from FEWS webservice for specific location-parameter combinations.
"""

import xml.etree.ElementTree as ET
from typing import Tuple, List

import httpx
from pydantic_ai import RunContext

from ...models.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
    TimeseriesValue,
)
from ...models.base import Deps
from ...utils.logging_utils import log_tool_call


def format_datetime(dt):
    """Format datetime to FEWS webservice format (yyyy-MM-dd'T'HH:mm:ss'Z')."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


async def parse_timeseries_xml(xml_content: str) -> Tuple[dict, List[TimeseriesValue]]:
    """
    Parse FEWS XML response into metadata and timeseries values.
    Handles missing values internally based on the missVal from header.

    Returns:
        Tuple[dict, List[TimeseriesValue]]: Metadata and list of values
    """
    root = ET.fromstring(xml_content)
    ns = {"pi": "http://www.wldelft.nl/fews/PI"}

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

        values.append(
            TimeseriesValue(
                datetime=f"{date}T{time}Z",
                location_id=metadata["location_id"],
                station_name=metadata["station_name"],
                parameter_id=metadata["parameter_id"],
                moduleinstance_id=metadata["moduleinstance_id"],
                value=value,
                flag=int(event.get("flag")),
            )
        )

    return metadata, values


def convert_to_csv(values: List[TimeseriesValue]) -> str:
    """
    Convert timeseries values to CSV format.
    """
    headers = [
        "datetime",
        "location_id",
        "station_name",
        "parameter_id",
        "moduleinstance_id",
        "value",
        "flag",
    ]

    # Create CSV string manually to ensure consistent line endings
    lines = [",".join(headers)]
    for value in values:
        data = value.model_dump()
        lines.append(",".join(str(data[h]) for h in headers))

    return "\n".join(lines)


@log_tool_call
async def get_series_data(
    ctx: RunContext[Deps], input: GetSeriesDataInput
) -> GetSeriesDataOutput:
    """
    Retrieve timeseries data for a specific location-parameter combination.

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

    # Fetch data from webservice
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.text}")
        xml_content = response.text

    # Parse response and convert to CSV
    metadata, values = await parse_timeseries_xml(xml_content)
    csv_data = convert_to_csv(values)

    return GetSeriesDataOutput(values=values, metadata=metadata, csv_data=csv_data)
