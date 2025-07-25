"""
Get series headers with incremental caching from FEWS webservice.

This tool retrieves series headers using an incremental caching approach. It first checks
the local DuckDB cache, and if data is not found, it triggers ingestion from the webservice.
"""

import xml.etree.ElementTree as ET

from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.utils.utils import to_iso
from talk_with_fews.utils.webservice_utils import get_request


@log_tool_call
async def get_series_statistics(
    ctx: RunContext[Deps], input: GetSeriesStatisticsInput
) -> GetSeriesStatisticsOutput:
    """
    Retrieve series statistics with incremental caching from FEWS webservice.

    This tool implements the incremental caching strategy: first check local cache,
    then trigger ingestion if needed, and return minimal but meaningful output.

    Args:
        ctx: RunContext with database connection
        input: GetSeriesHeadersInput containing parameter_id OR location_id

    Returns:
        GetSeriesHeadersOutput with series headers summary and follow-up suggestions
    """

    # Validate input
    if not input.parameter_id and not input.location_id:
        raise ValueError("Require both parameter_id and location_id")

    webservice_url = ctx.deps.webservice_url
    location_id = input.location_id
    parameter_id = input.parameter_id

    request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
    params = {
            "locationIds": location_id,
            "parameterIds": parameter_id,
            "onlyHeaders": "True",
            "showStatistics": "true",
            "documentFormat": "PI_XML",
        }

    # Fetch data from webservice
    error, xml_content = get_request(request_url, params=params)  # noqa: F821
    if error is not None:
        raise ValueError(f"Error fetching timeseries details: {error}")
    
    namespace = {"pi": "http://www.wldelft.nl/fews/PI"}

    # Parse the XML response
    root = ET.fromstring(xml_content)

    # Locate the series element (should be one per parameter_id or location_id)
    series_elem = root.find(".//pi:series", namespace)
    if series_elem is None:
        raise ValueError("No series element found in the response XML.")

    # Extract the header element containing metadata
    header_elem = series_elem.find("pi:header", namespace)
    if header_elem is None:
        raise ValueError("Missing series header information for the given parameter_id or location_id")

    # Extract valueCount information
    count_elem = header_elem.find("pi:valueCount", namespace)

    count = int(count_elem.text)
    if count == 0:
        return GetSeriesStatisticsOutput(
            count=0,
            description=f"No data found for parameter_id '{parameter_id}' or location_id '{location_id}'",
        )
    else:
        # Extract minValue and maxValue
        min_value_elem = header_elem.find("pi:minValue", namespace)
        max_value_elem = header_elem.find("pi:maxValue", namespace)
        min_value = min_value_elem.text if min_value_elem is not None else None
        max_value = max_value_elem.text if max_value_elem is not None else None
        
        # Extract first value time
        first_value_elem = header_elem.find("pi:firstValueTime", namespace)
        first_date = first_value_elem.get("date")
        first_time = first_value_elem.get("time")

        # Extract last value time
        last_value_elem = header_elem.find("pi:lastValueTime", namespace)
        last_date = last_value_elem.get("date")
        last_time = last_value_elem.get("time")
        
        # make into ISO 8601 format
        first_datetime = to_iso(first_date, first_time)
        last_datetime = to_iso(last_date, last_time)

        return GetSeriesStatisticsOutput(
            count=count,
            description=f"Found {count} series for parameter_id '{parameter_id}' or location_id '{location_id}'",
            min_value=min_value,
            max_value=max_value,
            first_value_time=first_datetime,
            last_value_time=last_datetime,
        )


