"""
Ingest series headers from FEWS webservice into local DuckDB cache.

This tool fetches series headers from the FEWS webservice and stores them in the local
DuckDB database for incremental caching. Supports both parameter-based and location-based queries.
"""

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from typing import List, Dict, Any
import duckdb
from datetime import datetime, timezone, timedelta
from pydantic_ai import ModelRetry
from talk_with_fews.models.base import SeriesHeader
from talk_with_fews.models.webservice.ingest_series_headers import (
    IngestSeriesHeadersOutput,
)
from talk_with_fews.utils.webservice_utils import get_timeseries_headers
import asyncio
import httpx
from talk_with_fews.utils.logging_utils import logger


def find_first_last_value_time(
    webservice_url: str,
    parameter_id: str = None,
    location_id: str = None,
    module_instance_id: str = None,
    max_attempts: int = 10,
    step_in_years: int = 5,
) -> tuple[dict[str, datetime], dict[str, datetime]]:
    """
    Find the last value time by starting 1990-01-01 until now.
    In some case this will fail, then we can use a 3 step approach.
    """
    # Start from a few months in the future to ensure we capture recent data
    current_time = datetime.now(timezone.utc) + timedelta(
        days=90
    )  # 3 months in the future

    # we search for 30 years back
    # FEWS is started in 1990, so start time is always after that
    start_time = datetime(1990, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    # Look back 30 years from current point
    end_time = current_time
    split_search_window = timedelta(
        days=step_in_years * 365
    )  # Start with 10, 5, 1 years steps to avoid missing recent data
    error_mode = False
    first_dates = dict()
    last_dates = dict()
    module_instance_ids = dict()
    for attempt in range(max_attempts):
        error, xml_content, _ = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            module_instance_id=module_instance_id,
            start_time=start_time,
            end_time=end_time,
            show_statistics=True,
            document_format="PI_XML",
        )
        if error or not xml_content:
            # if we get an error
            # Haven't found data yet, keep going backward
            end_time = start_time + split_search_window
            error_mode = True
            continue

        # Parse XML to find the LATEST lastValueTime across ALL series
        namespace = {"pi": "http://www.wldelft.nl/fews/PI"}
        try:
            root = ET.fromstring(xml_content)
            try:
                series_list = root.findall("pi:series", namespace)
            except ParseError:
                logger.warning("Failed to parse XML content")
                break
            for series_elem in series_list:
                header_elem = series_elem.find("pi:header", namespace)
                if header_elem is not None:
                    last_value_elem = header_elem.find("pi:lastValueTime", namespace)
                    if last_value_elem is not None:
                        # Parse the last value time for this series
                        module_instance_id = header_elem.find(
                            "pi:moduleInstanceId", namespace
                        )
                        last_date = last_value_elem.get("date")
                        last_time = last_value_elem.get("time")
                        if last_date and last_time:
                            last_datetime_str = f"{last_date}T{last_time}+00:00"
                            candidate_last_value = datetime.fromisoformat(
                                last_datetime_str
                            )
                            # store location and date combo, these could be different
                            # if we search on muliple locations, we keep them seperate
                            # we also need module_instance_id
                            if location_id is None:
                                found_location = header_elem.find(
                                    "pi:locationId", namespace
                                )
                                if found_location.text in last_dates:
                                    if (
                                        candidate_last_value
                                        > last_dates[found_location.text]
                                    ):
                                        last_dates[found_location.text] = (
                                            candidate_last_value
                                        )
                                else:
                                    last_dates[found_location.text] = (
                                        candidate_last_value
                                    )
                                    module_instance_ids[found_location.text] = (
                                        module_instance_id.text
                                    )

                            # if we serach on multiple parameters, keep them seperate
                            if parameter_id is None:
                                found_parameter = header_elem.find(
                                    "pi:parameterId", namespace
                                )
                                if found_parameter.text in first_dates:
                                    if (
                                        candidate_last_value
                                        > last_dates[found_parameter.text]
                                    ):
                                        last_dates[found_parameter.text] = (
                                            candidate_last_value
                                        )
                                else:
                                    last_dates[found_parameter.text] = (
                                        candidate_last_value
                                    )
                                    module_instance_ids[found_parameter.text] = (
                                        module_instance_id.text
                                    )

                    # repeat for first
                    first_value_elem = header_elem.find("pi:firstValueTime", namespace)
                    if first_value_elem is not None:
                        # Parse the last value time for this series
                        module_instance_id = header_elem.find(
                            "pi:moduleInstanceId", namespace
                        )
                        first_date = first_value_elem.get("date")
                        first_time = first_value_elem.get("time")
                        if first_date and first_time:
                            first_datetime_str = f"{first_date}T{first_time}+00:00"
                            candidate_first_value = datetime.fromisoformat(
                                first_datetime_str
                            )
                            if location_id is None:
                                found_location = header_elem.find(
                                    "pi:locationId", namespace
                                )
                                if found_location.text in first_dates:
                                    if (
                                        candidate_first_value
                                        > first_dates[found_location.text]
                                    ):
                                        first_dates[found_location.text] = (
                                            candidate_first_value
                                        )
                                else:
                                    first_dates[found_location.text] = (
                                        candidate_first_value
                                    )
                                    module_instance_ids[found_location.text] = (
                                        module_instance_id.text
                                    )

                            if parameter_id is None:
                                found_parameter = header_elem.find(
                                    "pi:parameterId", namespace
                                )
                                if found_parameter.text in first_dates:
                                    if (
                                        candidate_first_value
                                        > first_dates[found_parameter.text]
                                    ):
                                        first_dates[found_parameter.text] = (
                                            candidate_first_value
                                        )
                                else:
                                    first_dates[found_parameter.text] = (
                                        candidate_first_value
                                    )
                                    module_instance_ids[found_parameter.text] = (
                                        module_instance_id.text
                                    )
        except Exception:
            pass

        # if we fail to get 30 years, we stop and split it into 3 chunks
        if error_mode and end_time < current_time:
            # if we were in error mode, reset end_time to current time
            end_time += split_search_window
            start_time += split_search_window
        # if we got a value the first time or we completed 3 searches, we can stop
        else:
            break

    if len(first_dates) > 0 or len(last_dates) > 0:
        return first_dates, last_dates, module_instance_ids
    else:
        return None, None, None


def discover_all_series(
    webservice_url: str,
    parameter_ids: list = None,
    location_ids: list = None,
    show_statistics: bool = False,
) -> dict:
    """
    Discover all available series combinations with a single API call.
    This is much faster than the iterative approach when we just need to discover series.

    Args:
        webservice_url: Base URL of the FEWS webservice
        show_statistics: Whether to include statistics in the response

    Returns:
        Dictionary mapping (module_instance_id, location_id, parameter_id) to series metadata
    """
    print("Discovering all available series with single API call...")

    # Make a single API call to get available series for the specified parameters/locations
    param_ids_str = ",".join(parameter_ids) if parameter_ids else None
    location_ids_str = ",".join(location_ids) if location_ids else None

    error, xml_content, _ = get_timeseries_headers(
        webservice_url=webservice_url,
        parameter_id=param_ids_str,  # Filter by parameters
        location_id=location_ids_str,  # Filter by locations
        module_instance_id=None,  # No module filter - get all
        start_time=None,  # No time filter - get all
        end_time=None,  # No time filter - get all
        show_statistics=show_statistics,
        document_format="PI_XML",
    )

    if error:
        print(f"Error discovering series: {error}")
        return {}

    if not xml_content:
        print("No XML content received")
        return {}

    # Parse the XML to extract series information
    series_data = {}

    try:
        import xml.etree.ElementTree as ET

        # Debug: Check XML content
        print(f"XML content length: {len(xml_content)}")
        print(f"XML starts with: {xml_content[:200]}")
        print(f"XML ends with: {xml_content[-200:]}")

        root = ET.fromstring(xml_content)

        # Find all series elements - try different namespace approaches
        series_elements = root.findall(".//series")
        if not series_elements:
            # Try with namespace
            series_elements = root.findall(".//{http://www.wldelft.nl/fews/PI}series")

        print(f"Found {len(series_elements)} series elements in XML")

        for i, series in enumerate(series_elements):
            # Extract series metadata from header element (not directly on series)
            # Try both with and without namespace
            header_elem = series.find("header")
            if header_elem is None:
                # Try with namespace
                header_elem = series.find("{http://www.wldelft.nl/fews/PI}header")

            if header_elem is None:
                if i < 3:
                    print(f"  Series {i}: No header element found")
                continue

            # Try both with and without namespace for child elements
            module_instance_id = header_elem.find(
                "moduleInstanceId"
            ) or header_elem.find("{http://www.wldelft.nl/fews/PI}moduleInstanceId")
            location_id_elem = header_elem.find("locationId") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}locationId"
            )
            parameter_id_elem = header_elem.find("parameterId") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}parameterId"
            )

            # Extract text content from elements
            module_instance_id = (
                module_instance_id.text if module_instance_id is not None else None
            )
            location_id = (
                location_id_elem.text if location_id_elem is not None else None
            )
            parameter_id = (
                parameter_id_elem.text if parameter_id_elem is not None else None
            )

            # Debug: Print first few series to understand structure
            if i < 3:
                print(
                    f"  Series {i}: moduleInstanceId='{module_instance_id}', locationId='{location_id}', parameterId='{parameter_id}'"
                )

            if not all([module_instance_id, location_id, parameter_id]):
                if i < 3:
                    print(f"    Skipping series {i}: missing required attributes")
                continue

            # Extract time information from header element
            first_value_time = None
            last_value_time = None
            has_data = False

            first_value_elem = header_elem.find("firstValueTime") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}firstValueTime"
            )
            if first_value_elem is not None and first_value_elem.text:
                try:
                    first_value_time = datetime.fromisoformat(
                        first_value_elem.text.replace("Z", "+00:00")
                    )
                    has_data = True
                except ValueError:
                    pass

            last_value_elem = header_elem.find("lastValueTime") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}lastValueTime"
            )
            if last_value_elem is not None and last_value_elem.text:
                try:
                    last_value_time = datetime.fromisoformat(
                        last_value_elem.text.replace("Z", "+00:00")
                    )
                    has_data = True
                except ValueError:
                    pass

            # Extract other metadata from header element
            type_elem = header_elem.find("type") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}type"
            )
            series_type = type_elem.text if type_elem is not None else None

            time_step_elem = header_elem.find("timeStep") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}timeStep"
            )
            time_step_unit = None
            time_step_multiplier = None
            if time_step_elem is not None:
                time_step_unit = time_step_elem.get("unit")
                time_step_multiplier = time_step_elem.get("multiplier")
                if time_step_multiplier:
                    try:
                        time_step_multiplier = int(time_step_multiplier)
                    except ValueError:
                        time_step_multiplier = None

            miss_val_elem = header_elem.find("missVal") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}missVal"
            )
            miss_val = None
            if miss_val_elem is not None and miss_val_elem.text:
                try:
                    miss_val = float(miss_val_elem.text)
                except ValueError:
                    pass

            time_zone_elem = header_elem.find("timeZone") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}timeZone"
            )
            time_zone = time_zone_elem.text if time_zone_elem is not None else None

            qualifiers_elem = header_elem.find("qualifiers") or header_elem.find(
                "{http://www.wldelft.nl/fews/PI}qualifiers"
            )
            qualifiers = qualifiers_elem.text if qualifiers_elem is not None else None

            # Store the series data
            series_key = (module_instance_id, location_id, parameter_id)
            series_data[series_key] = {
                "type": series_type,
                "timeStepUnit": time_step_unit,
                "timeStepMultiplier": time_step_multiplier,
                "missVal": miss_val,
                "timeZone": time_zone,
                "qualifiers": qualifiers,
                "firstValueTime": first_value_time,
                "lastValueTime": last_value_time,
                "hasData": has_data,
            }

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {}
    except Exception as e:
        print(f"Error processing series data: {e}")
        return {}

    print(f"Discovered {len(series_data)} series combinations")
    return series_data


def find_series_data_range(
    webservice_url: str,
    parameter_ids: list = None,
    location_ids: list = None,
    module_instance_id: str = None,
    max_attempts: int = 20,
    show_statistics: bool = True,
) -> dict:
    """
    Find the data range for all series combinations by working backward iteratively.

    Returns a dictionary with series data:
    {
        (moduleInstanceId, locationId, parameterId): {
            'firstValueTime': datetime,
            'lastValueTime': datetime,
            'hasData': bool
        }
    }
    """
    # Track individual series data
    series_data = {}  # key: (moduleInstanceId, locationId, parameterId)
    completed_series = set()  # Series we've found complete data for

    # Start from current time and work backward
    current_end = datetime.now(timezone.utc)

    for attempt in range(max_attempts):
        # Work backward with adaptive step sizes
        step_days = min(
            365, 365 * (attempt + 1) // 5
        )  # Start with 1 year, increase gradually
        current_start = current_end - timedelta(days=step_days)

        # Prevent going too far back
        if current_start < datetime(2000, 1, 1, tzinfo=timezone.utc):
            current_start = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Prevent invalid time ranges
        if current_start >= current_end:
            break

        print(f"Searching series data: {current_start} to {current_end}")

        # Build comma-separated parameter and location IDs for batched API call
        param_ids_str = ",".join(parameter_ids) if parameter_ids else None
        location_ids_str = ",".join(location_ids) if location_ids else None

        error, xml_content, _ = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=param_ids_str,
            location_id=location_ids_str,
            module_instance_id=module_instance_id,
            start_time=current_start,
            end_time=current_end,
            show_statistics=show_statistics,
            document_format="PI_XML",
        )

        if error or not xml_content:
            # No data in this range, move further back
            current_end = current_start - timedelta(days=1)
            continue

        # Parse XML to extract all series data
        namespace = {"pi": "http://www.wldelft.nl/fews/PI"}
        try:
            root = ET.fromstring(xml_content)
            series_elements = root.findall("pi:series", namespace)

            print(f"Found {len(series_elements)} series elements")

            for series_elem in series_elements:
                header_elem = series_elem.find("pi:header", namespace)
                if header_elem is not None:
                    # Extract series identifiers
                    module_id = header_elem.find("pi:moduleInstanceId", namespace)
                    location_id_elem = header_elem.find("pi:locationId", namespace)
                    param_id_elem = header_elem.find("pi:parameterId", namespace)

                    if (
                        module_id is not None
                        and location_id_elem is not None
                        and param_id_elem is not None
                    ):
                        series_key = (
                            module_id.text,
                            location_id_elem.text,
                            param_id_elem.text,
                        )

                        # Skip if we already have complete data for this series
                        if series_key in completed_series:
                            print(f"Skipping completed series: {series_key}")
                            continue

                        # Check if this series has data
                        value_count_elem = header_elem.find("pi:valueCount", namespace)
                        has_data = (
                            value_count_elem is not None
                            and int(value_count_elem.text) > 0
                        )

                        if has_data:
                            # Extract first and last value times
                            first_value_elem = header_elem.find(
                                "pi:firstValueTime", namespace
                            )
                            last_value_elem = header_elem.find(
                                "pi:lastValueTime", namespace
                            )

                            first_time = None
                            last_time = None

                            if first_value_elem is not None:
                                first_date = first_value_elem.get("date")
                                first_time_str = first_value_elem.get("time")
                                if first_date and first_time_str:
                                    first_datetime_str = (
                                        f"{first_date}T{first_time_str}+00:00"
                                    )
                                    first_time = datetime.fromisoformat(
                                        first_datetime_str
                                    )

                            if last_value_elem is not None:
                                last_date = last_value_elem.get("date")
                                last_time_str = last_value_elem.get("time")
                                if last_date and last_time_str:
                                    last_datetime_str = (
                                        f"{last_date}T{last_time_str}+00:00"
                                    )
                                    last_time = datetime.fromisoformat(
                                        last_datetime_str
                                    )

                            # Extract additional metadata (only if present in XML)
                            type_elem = header_elem.find("pi:type", namespace)
                            time_step_elem = header_elem.find("pi:timeStep", namespace)
                            miss_val_elem = header_elem.find("pi:missVal", namespace)
                            time_zone_elem = header_elem.find("pi:timeZone", namespace)
                            qualifiers_elem = header_elem.find(
                                "pi:qualifiers", namespace
                            )

                            # Parse timeStep element (has unit and multiplier attributes)
                            time_step_unit = None
                            time_step_multiplier = None
                            if time_step_elem is not None:
                                time_step_unit = time_step_elem.get("unit")
                                time_step_multiplier = time_step_elem.get("multiplier")
                                if time_step_multiplier is not None:
                                    time_step_multiplier = int(time_step_multiplier)

                            # Store series data with actual metadata from API
                            series_data[series_key] = {
                                "firstValueTime": first_time,
                                "lastValueTime": last_time,
                                "hasData": True,
                                "type": type_elem.text
                                if type_elem is not None
                                else None,
                                "timeStepUnit": time_step_unit,
                                "timeStepMultiplier": time_step_multiplier,
                                "missVal": float(miss_val_elem.text)
                                if miss_val_elem is not None and miss_val_elem.text
                                else None,
                                "timeZone": time_zone_elem.text
                                if time_zone_elem is not None
                                else None,
                                "qualifiers": qualifiers_elem.text
                                if qualifiers_elem is not None
                                else None,
                            }

                            print(
                                f"Found series data: {series_key} -> {first_time} to {last_time}"
                            )

                            # Mark as completed if we have both first and last times
                            if first_time and last_time:
                                completed_series.add(series_key)
                                print(f"Series completed: {series_key}")
                    else:
                        # Series exists but has no data - still extract metadata if available
                        type_elem = header_elem.find("pi:type", namespace)
                        time_step_elem = header_elem.find("pi:timeStep", namespace)
                        miss_val_elem = header_elem.find("pi:missVal", namespace)
                        time_zone_elem = header_elem.find("pi:timeZone", namespace)
                        qualifiers_elem = header_elem.find("pi:qualifiers", namespace)

                        # Parse timeStep element (has unit and multiplier attributes)
                        time_step_unit = None
                        time_step_multiplier = None
                        if time_step_elem is not None:
                            time_step_unit = time_step_elem.get("unit")
                            time_step_multiplier = time_step_elem.get("multiplier")
                            if time_step_multiplier is not None:
                                time_step_multiplier = int(time_step_multiplier)

                        series_data[series_key] = {
                            "firstValueTime": None,
                            "lastValueTime": None,
                            "hasData": False,
                            "type": type_elem.text if type_elem is not None else None,
                            "timeStepUnit": time_step_unit,
                            "timeStepMultiplier": time_step_multiplier,
                            "missVal": float(miss_val_elem.text)
                            if miss_val_elem is not None and miss_val_elem.text
                            else None,
                            "timeZone": time_zone_elem.text
                            if time_zone_elem is not None
                            else None,
                            "qualifiers": qualifiers_elem.text
                            if qualifiers_elem is not None
                            else None,
                        }
                        print(f"Series has no data: {series_key}")

        except Exception as e:
            print(f"XML parsing error: {e}")
            pass

        # Move further back for next iteration
        current_end = current_start - timedelta(days=1)

    print(
        f"Search completed. Found {len(series_data)} series, {len(completed_series)} completed"
    )
    return series_data


def validate_foreign_keys(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    location_id: str,
    parameter_id: str,
) -> bool:
    """Validate that location and parameter exist before inserting series header"""

    # Check if location exists
    location_exists = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM locations WHERE locationId = ?
    """,
        [location_id],
    ).fetchone()[0]

    # Check if parameter exists
    parameter_exists = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM parameters WHERE id = ?
    """,
        [parameter_id],
    ).fetchone()[0]

    return location_exists > 0 and parameter_exists > 0


def parse_series_headers_xml(xml_content: str, start_id: int) -> List[SeriesHeader]:
    """Parse XML content and extract series headers"""

    # Define namespace for PI_XML format
    namespace = {"pi": "http://www.wldelft.nl/fews/PI"}

    # Parse XML
    root = ET.fromstring(xml_content)

    series_headers = []

    # Find all series elements
    for series_elem in root.findall(".//pi:series", namespace):
        # Extract series header information
        header_elem = series_elem.find("pi:header", namespace)
        if header_elem is None:
            continue

        # Extract timeStep information
        time_step_elem = header_elem.find("pi:timeStep", namespace)
        time_step_unit = (
            time_step_elem.get("unit") if time_step_elem is not None else None
        )
        # Handle timeStep multiplier based on unit type
        time_step_multiplier = 1  # Default for equidistant time steps
        if time_step_elem is not None:
            unit = time_step_elem.get("unit")
            if unit == "nonequidistant":
                # For nonequidistant time steps, multiplier is not applicable
                # Use 0 to indicate irregular intervals
                time_step_multiplier = 0
            else:
                # For equidistant time steps, use the multiplier if present
                multiplier_attr = time_step_elem.get("multiplier")
                if multiplier_attr is not None:
                    time_step_multiplier = int(multiplier_attr)

        # Extract qualifiers
        qualifiers_elem = header_elem.find("pi:qualifiers", namespace)
        qualifiers = qualifiers_elem.text if qualifiers_elem is not None else None

        # Extract time range information (when showStatistics=true)
        first_value_time = None
        last_value_time = None

        # Extract time range information (when showStatistics=true)
        # Use firstValueTime/lastValueTime which represent actual data availability
        # Do NOT use startDate/endDate as they represent requested time range, not actual data
        first_value_elem = header_elem.find("pi:firstValueTime", namespace)
        last_value_elem = header_elem.find("pi:lastValueTime", namespace)

        if first_value_elem is not None and last_value_elem is not None:
            first_date = first_value_elem.get("date")
            first_time = first_value_elem.get("time")
            last_date = last_value_elem.get("date")
            last_time = last_value_elem.get("time")

            if first_date and first_time and last_date and last_time:
                try:
                    # Convert to datetime objects
                    first_datetime = datetime.strptime(
                        f"{first_date} {first_time}", "%Y-%m-%d %H:%M:%S"
                    )
                    last_datetime = datetime.strptime(
                        f"{last_date} {last_time}", "%Y-%m-%d %H:%M:%S"
                    )

                    # Apply timezone if available
                    timezone_elem = root.find("pi:timeZone", namespace)
                    if timezone_elem is not None and timezone_elem.text:
                        timezone_offset = float(timezone_elem.text)
                        tz = timezone(timedelta(hours=timezone_offset))
                        if timezone_offset != 0:
                            first_datetime = first_datetime.replace(
                                tzinfo=tz
                            ).astimezone(timezone.utc)
                            last_datetime = last_datetime.replace(tzinfo=tz).astimezone(
                                timezone.utc
                            )
                        else:
                            first_datetime = first_datetime.replace(tzinfo=timezone.utc)
                            last_datetime = last_datetime.replace(tzinfo=timezone.utc)
                    else:
                        # Default to UTC if no timezone info
                        first_datetime = first_datetime.replace(tzinfo=timezone.utc)
                        last_datetime = last_datetime.replace(tzinfo=timezone.utc)

                    first_value_time = first_datetime
                    last_value_time = last_datetime

                except (ValueError, TypeError) as e:
                    print(f"Warning: Could not parse time information: {e}")
                    first_value_time = None
                    last_value_time = None

        # Get required fields - these are ELEMENTS, not ATTRIBUTES!
        location_id_elem = header_elem.find("pi:locationId", namespace)
        parameter_id_elem = header_elem.find("pi:parameterId", namespace)
        module_instance_id_elem = header_elem.find("pi:moduleInstanceId", namespace)
        series_type_elem = header_elem.find("pi:type", namespace)

        # Extract text content from elements
        location_id = location_id_elem.text if location_id_elem is not None else ""
        parameter_id = parameter_id_elem.text if parameter_id_elem is not None else ""
        module_instance_id = (
            module_instance_id_elem.text if module_instance_id_elem is not None else ""
        )
        series_type = series_type_elem.text if series_type_elem is not None else ""

        # Log problematic entries
        if not location_id or not parameter_id:
            print(
                f"Warning: Series header with missing data - locationId='{location_id}', parameterId='{parameter_id}', moduleInstanceId='{module_instance_id}'"
            )
            # Skip entries with missing critical data
            continue

        # Create SeriesHeader object
        series_header = SeriesHeader(
            id=start_id,  # auto-increment for now
            type=series_type,
            moduleInstanceId=module_instance_id,
            locationId=location_id,
            parameterId=parameter_id,
            timeStepUnit=time_step_unit or "",
            timeStepMultiplier=time_step_multiplier,
            missVal=float(header_elem.get("missVal", 0)),
            timeZone=header_elem.get("timeZone", ""),
            qualifiers=qualifiers,
            first_value_time=first_value_time,
            last_value_time=last_value_time,
        )
        # Increment for next series header
        series_headers.append(series_header)
        start_id += 1

    return series_headers


def insert_series_header(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    series_header: SeriesHeader,
    skip_empty_data: bool = True,
) -> bool:
    """Insert series header with foreign key validation and optional empty data filtering"""

    # Validate foreign keys before insertion
    if not validate_foreign_keys(
        cache_FewsWebServices_db, series_header.locationId, series_header.parameterId
    ):
        print(
            f"Warning: Foreign key validation failed for locationId={series_header.locationId}, parameterId={series_header.parameterId}"
        )
        return False

    # Skip series headers that have no actual data (both first_value_time and last_value_time are None)
    if (
        skip_empty_data
        and series_header.first_value_time is None
        and series_header.last_value_time is None
    ):
        print(
            f"Skipping series header with no data: locationId={series_header.locationId}, parameterId={series_header.parameterId}"
        )
        return False

    # Check if this series already exists (deduplication)
    existing = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM series_headers
        WHERE locationId = ? AND parameterId = ? AND moduleInstanceId = ?
    """,
        [
            series_header.locationId,
            series_header.parameterId,
            series_header.moduleInstanceId,
        ],
    ).fetchone()[0]

    if existing > 0:
        return False  # Already exists, skip insertion

    # Insert the series header
    cache_FewsWebServices_db.execute(
        """
        INSERT INTO series_headers (
            id, type, moduleInstanceId, locationId, parameterId,
            timeStepUnit, timeStepMultiplier, missVal, timeZone, qualifiers,
            first_value_time, last_value_time
        ) VALUES (nextval('series_headers_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        [
            series_header.type,
            series_header.moduleInstanceId,
            series_header.locationId,
            series_header.parameterId,
            series_header.timeStepUnit,
            series_header.timeStepMultiplier,
            series_header.missVal,
            series_header.timeZone,
            series_header.qualifiers,
            series_header.first_value_time,
            series_header.last_value_time,
        ],
    )

    return True


async def ingest_series_headers(
    webservice_url: str,
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_id: str = None,
    location_id: str = None,
    skip_empty_data: bool = True,
) -> IngestSeriesHeadersOutput:
    """
    Ingest series headers from FEWS webservice into local DuckDB cache.

    Args:
        webservice_url: URL of the FEWS webservice
        cache_FewsWebServices_db: DuckDB connection for caching
        parameter_id: Parameter ID to ingest series headers for
        location_id: Location ID to ingest series headers for
        skip_empty_data: If True (default), skip location-parameter combinations that have no actual time series data

    Returns:
        IngestSeriesHeadersOutput with status and SQL examples
    """

    # Validate input - must have either parameter_id or location_id, not both
    if parameter_id and location_id:
        raise ModelRetry("Cannot specify both parameter_id and location_id")
    if not parameter_id and not location_id:
        raise ModelRetry("Must specify either parameter_id or location_id")

    # Define query_type early for use in error handling
    query_type = (
        f"parameter {parameter_id}" if parameter_id else f"location {location_id}"
    )

    try:
        # Use iterative approach to find true data availability range
        # This is more efficient than large time windows and avoids server memory issues
        print(f"Finding true data availability range for {query_type}...")
        first_value_time_dict, last_value_time_dict, module_instance_ids = (
            find_first_last_value_time(
                webservice_url=webservice_url,
                parameter_id=parameter_id,
                location_id=location_id,
                step_in_years=10,
            )
        )
        # not clean but should work?
        if first_value_time_dict is None or last_value_time_dict is None:
            first_value_time_dict, last_value_time_dict, module_instance_ids = (
                find_first_last_value_time(
                    webservice_url=webservice_url,
                    parameter_id=parameter_id,
                    location_id=location_id,
                    step_in_years=5,
                )
            )
            if first_value_time_dict is None or last_value_time_dict is None:
                first_value_time_dict, last_value_time_dict, module_instance_ids = (
                    find_first_last_value_time(
                        webservice_url=webservice_url,
                        parameter_id=parameter_id,
                        location_id=location_id,
                        step_in_years=1,
                    )
                )
                if first_value_time_dict is None or last_value_time_dict is None:
                    # no first or last date found
                    return IngestSeriesHeadersOutput(
                        description="error retrieving series headers",
                        series_count=0,
                        sql_examples=[""],
                    )
        inserted_count = 0
        skipped_count = 0
        if parameter_id is None:
            for parameter_id in first_value_time_dict:
                module_instance_id = module_instance_ids[parameter_id]
                first_value_time = first_value_time_dict[parameter_id]
                try:
                    last_value_time = last_value_time_dict[parameter_id]
                except KeyError:
                    continue
                inserted_count, skipped_count = fill_cache(
                    webservice_url,
                    parameter_id,
                    location_id,
                    module_instance_id,
                    first_value_time,
                    last_value_time,
                    query_type,
                    cache_FewsWebServices_db,
                    skip_empty_data,
                    inserted_count,
                    skipped_count,
                )
        else:
            for location_id in first_value_time_dict:
                module_instance_id = module_instance_ids[location_id]
                first_value_time = first_value_time_dict[location_id]
                try:
                    last_value_time = last_value_time_dict[location_id]
                except KeyError:
                    continue
                inserted_count, skipped_count = fill_cache(
                    webservice_url,
                    parameter_id,
                    location_id,
                    module_instance_id,
                    first_value_time,
                    last_value_time,
                    query_type,
                    cache_FewsWebServices_db,
                    skip_empty_data,
                    inserted_count,
                    skipped_count,
                )
    except ValueError as e:
        # Re-raise with context
        raise ValueError(f"Error fetching series headers for {query_type}: {e}")

    sql_examples = [
        f"SELECT COUNT(*) FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}'",
        f"SELECT * FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}' LIMIT 5",
        "SELECT sh.*, l.shortName, p.name FROM series_headers sh JOIN locations l ON sh.locationId = l.locationId JOIN parameters p ON sh.parameterId = p.id LIMIT 5",
        "SELECT locationId, parameterId, first_value_time, last_value_time FROM series_headers WHERE first_value_time IS NOT NULL ORDER BY first_value_time DESC LIMIT 10",
    ]
    # Build description message
    description_parts = [
        f"Successfully ingested {inserted_count} series headers for {query_type}"
    ]
    if skip_empty_data and skipped_count > 0:
        description_parts.append(f"Skipped {skipped_count} series headers with no data")

    return IngestSeriesHeadersOutput(
        description=". ".join(description_parts),
        series_count=inserted_count,
        sql_examples=sql_examples,
    )


def fill_cache(
    webservice_url,
    parameter_id,
    location_id,
    module_instance_id,
    first_value_time,
    last_value_time,
    query_type,
    cache_FewsWebServices_db,
    skip_empty_data,
    inserted_count,
    skipped_count,
):
    # Now make the actual API call with the discovered range
    # Try with statistics first, fall back to without if not supported
    error, data, request_time = get_timeseries_headers(
        webservice_url=webservice_url,
        parameter_id=parameter_id,
        module_instance_id=module_instance_id,
        location_id=location_id,
        start_time=first_value_time,
        end_time=last_value_time,
        show_statistics=True,  # Try with statistics first
        document_format="PI_XML",  # Use XML format for proper header discovery with statistics
        # Note: CSV format doesn't respect onlyHeaders=True parameter in this FEWS implementation
        # CSV always returns full time series data, not just headers with statistics
    )

    # If statistics are not supported by this API, try without
    if error and "unexpected parameter" in str(error).lower():
        print("Statistics not supported by this API, trying without...")
        error, data, request_time = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            module_instance_id=module_instance_id,
            start_time=first_value_time,
            end_time=last_value_time,
            show_statistics=False,  # Try without statistics
            document_format="PI_XML",
        )

    # if the range is too large, split into smaller chunks
    elif error and "OutofMemory" in str(error).lower():
        return IngestSeriesHeadersOutput(
            description=f"No time series found for {query_type}",
            series_count=0,
            sql_examples=[],
        )
    elif error is None and data is None:
        # No data found - this is normal
        return IngestSeriesHeadersOutput(
            description=f"No time series found for {query_type}",
            series_count=0,
            sql_examples=[],
        )

    latest_id = cache_FewsWebServices_db.execute(
        "SELECT COALESCE(MAX(id), 0) FROM series_headers"
    ).fetchone()[0]
    start_id = latest_id + 1
    series_headers = parse_series_headers_xml(data, start_id)

    for series_header in series_headers:
        if insert_series_header(
            cache_FewsWebServices_db, series_header, skip_empty_data
        ):
            inserted_count += 1
        elif (
            skip_empty_data
            and series_header.first_value_time is None
            and series_header.last_value_time is None
        ):
            skipped_count += 1

    return inserted_count, skipped_count


async def discover_all_series_async(
    webservice_url: str,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    show_statistics: bool = False,
    max_concurrent: int = 20,
) -> Dict[str, Dict[tuple, Dict[str, Any]]]:
    """
    Async version of discover_all_series for high-performance parallel processing.

    Uses httpx.AsyncClient with connection pooling and HTTP/2 support for optimal
    performance when processing many parameters in parallel.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        show_statistics: Whether to include statistics in the response
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Dictionary mapping parameter_id -> series_data (same format as discover_all_series)
    """
    # Configure connection limits for optimal performance
    limits = httpx.Limits(
        max_connections=max_concurrent,
        max_keepalive_connections=max_concurrent,
        keepalive_expiry=30.0,
    )

    # Configure timeout
    timeout = httpx.Timeout(60.0, connect=10.0)

    results = {}

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        http2=True,  # Enable HTTP/2 for better multiplexing
    ) as client:

        async def fetch_series_data(
            request_params: dict,
        ) -> tuple[str, Dict[tuple, Dict[str, Any]]]:
            """Fetch series data for given parameters/locations."""
            try:
                # Construct request URL and parameters
                request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
                params = {
                    "onlyHeaders": "True",
                    "documentFormat": "PI_XML",
                }

                # Add parameter and location filters
                if request_params.get("parameter_ids"):
                    params["parameterIds"] = ",".join(request_params["parameter_ids"])
                if request_params.get("location_ids"):
                    params["locationIds"] = ",".join(request_params["location_ids"])
                if show_statistics:
                    params["showStatistics"] = "true"

                # Make async request
                response = await client.get(request_url, params=params)
                response.raise_for_status()

                xml_content = response.text
                logger.info(f"📄 Response size: {len(xml_content)} characters")

                # Parse XML and extract series data
                series_data = {}

                try:
                    root = ET.fromstring(xml_content)

                    # Find all series elements - try different namespace approaches
                    series_elements = root.findall(".//series")
                    if not series_elements:
                        # Try with namespace
                        series_elements = root.findall(
                            ".//{http://www.wldelft.nl/fews/PI}series"
                        )

                    logger.info(f"Found {len(series_elements)} series elements in XML")

                    for i, series in enumerate(series_elements):
                        # Extract series metadata from header element (not directly on series)
                        # Try both with and without namespace
                        header_elem = series.find("header")
                        if header_elem is None:
                            # Try with namespace
                            header_elem = series.find(
                                "{http://www.wldelft.nl/fews/PI}header"
                            )

                        if header_elem is None:
                            continue

                        # Try both with and without namespace for child elements
                        module_instance_id = header_elem.find(
                            "moduleInstanceId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}moduleInstanceId"
                        )
                        location_id_elem = header_elem.find(
                            "locationId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}locationId"
                        )
                        parameter_id_elem = header_elem.find(
                            "parameterId"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}parameterId"
                        )

                        # Extract text content from elements
                        module_instance_id = (
                            module_instance_id.text
                            if module_instance_id is not None
                            else None
                        )
                        location_id = (
                            location_id_elem.text
                            if location_id_elem is not None
                            else None
                        )
                        parameter_id = (
                            parameter_id_elem.text
                            if parameter_id_elem is not None
                            else None
                        )

                        if not all([module_instance_id, location_id, parameter_id]):
                            continue

                        # Extract time information from header element
                        first_value_time = None
                        last_value_time = None
                        has_data = False

                        first_value_elem = header_elem.find(
                            "firstValueTime"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}firstValueTime"
                        )
                        if first_value_elem is not None and first_value_elem.text:
                            try:
                                first_value_time = datetime.fromisoformat(
                                    first_value_elem.text.replace("Z", "+00:00")
                                )
                                has_data = True
                            except ValueError:
                                pass

                        last_value_elem = header_elem.find(
                            "lastValueTime"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}lastValueTime"
                        )
                        if last_value_elem is not None and last_value_elem.text:
                            try:
                                last_value_time = datetime.fromisoformat(
                                    last_value_elem.text.replace("Z", "+00:00")
                                )
                                has_data = True
                            except ValueError:
                                pass

                        # Extract other metadata from header element
                        type_elem = header_elem.find("type") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}type"
                        )
                        series_type = type_elem.text if type_elem is not None else None

                        time_step_elem = header_elem.find(
                            "timeStep"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeStep")
                        time_step_unit = None
                        time_step_multiplier = None
                        if time_step_elem is not None:
                            time_step_unit = time_step_elem.get("unit")
                            time_step_multiplier = time_step_elem.get("multiplier")
                            if time_step_multiplier:
                                try:
                                    time_step_multiplier = int(time_step_multiplier)
                                except ValueError:
                                    time_step_multiplier = None

                        miss_val_elem = header_elem.find("missVal") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}missVal"
                        )
                        miss_val = None
                        if miss_val_elem is not None and miss_val_elem.text:
                            try:
                                miss_val = float(miss_val_elem.text)
                            except ValueError:
                                pass

                        time_zone_elem = header_elem.find(
                            "timeZone"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeZone")
                        time_zone = (
                            time_zone_elem.text if time_zone_elem is not None else None
                        )

                        qualifiers_elem = header_elem.find(
                            "qualifiers"
                        ) or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}qualifiers"
                        )
                        qualifiers = (
                            qualifiers_elem.text
                            if qualifiers_elem is not None
                            else None
                        )

                        # Store the series data
                        series_key = (module_instance_id, location_id, parameter_id)
                        series_data[series_key] = {
                            "type": series_type,
                            "moduleInstanceId": module_instance_id,
                            "locationId": location_id,
                            "parameterId": parameter_id,
                            "timeStepUnit": time_step_unit,
                            "timeStepMultiplier": time_step_multiplier,
                            "missVal": miss_val,
                            "timeZone": time_zone,
                            "qualifiers": qualifiers,
                            "firstValueTime": first_value_time,
                            "lastValueTime": last_value_time,
                            "hasData": has_data,
                        }

                except ET.ParseError as e:
                    logger.error(f"Error parsing XML for parameter {param_id}: {e}")
                    return param_id, {}
                except Exception as e:
                    logger.error(
                        f"Error processing series data for parameter {param_id}: {e}"
                    )
                    return param_id, {}

                # Create a key for the request (either parameter or location based)
                request_key = (
                    "params_" + "_".join(request_params.get("parameter_ids", []))
                    if request_params.get("parameter_ids")
                    else "locs_" + "_".join(request_params.get("location_ids", []))
                )

                logger.info(
                    f"Discovered {len(series_data)} series combinations for {request_key}"
                )
                return request_key, series_data

            except Exception as e:
                logger.error(f"Error fetching series for {request_params}: {e}")
                return "error", {}

        # Process requests with controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(request_params: dict):
            async with semaphore:
                return await fetch_series_data(request_params)

        # Create request tasks based on what we're processing
        tasks = []

        if parameter_ids:
            # Process each parameter individually
            for param_id in parameter_ids:
                tasks.append(fetch_with_semaphore({"parameter_ids": [param_id]}))
        elif location_ids:
            # Process each location individually
            for location_id in location_ids:
                tasks.append(fetch_with_semaphore({"location_ids": [location_id]}))
        else:
            # Process as a single batch request
            request_params = {}
            if parameter_ids:
                request_params["parameter_ids"] = parameter_ids
            if location_ids:
                request_params["location_ids"] = location_ids
            tasks.append(fetch_with_semaphore(request_params))

        # Execute all tasks concurrently
        logger.info(
            f"Starting async processing of {len(tasks)} requests with max {max_concurrent} concurrent requests"
        )
        start_time = datetime.now()

        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Completed async processing in {duration:.2f} seconds")

        # Process results
        for result in completed_tasks:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                continue

            request_key, series_data = result
            results[request_key] = series_data

    return results


def find_last_value_time(
    webservice_url: str,
    parameter_id: str = None,
    location_id: str = None,
    module_instance_id: str = None,
    max_attempts: int = 10,
) -> datetime:
    """
    Find the last value time by starting from future time and working backwards.

    Uses an iterative approach starting from 3 months in the future and moving backwards
    until we find the actual last data point. This ensures we capture recent data that
    might still be actively collected or processed.

    Starting from the future is important because:
    - Data might be collected in real-time or near real-time
    - Processing delays might mean recent data isn't immediately available
    - Starting from current time might miss the most recent data points
    """
    # Start from a few months in the future to ensure we capture recent data
    current_time = datetime.now(timezone.utc) + timedelta(
        days=90
    )  # 3 months in the future
    step_back = timedelta(
        days=30
    )  # Start with 1 month steps to avoid missing recent data

    global_latest_last_value = None
    found_data = False

    for attempt in range(max_attempts):
        start_time = current_time - timedelta(
            days=30
        )  # Look back 30 days from current point
        end_time = current_time

        error, xml_content, _ = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            module_instance_id=module_instance_id,
            start_time=start_time,
            end_time=end_time,
            show_statistics=True,
            document_format="PI_XML",
        )

        if error or not xml_content:
            # No data in this range
            if found_data:
                # We already found data, so we can stop here
                # Don't move forward beyond current time to avoid future dates
                break
            else:
                # Haven't found data yet, keep going backward
                current_time -= step_back
                step_back = min(
                    step_back * 1.5, timedelta(days=365)
                )  # Max 1 year steps
            continue

        # Parse XML to find the LATEST lastValueTime across ALL series
        namespace = {"pi": "http://www.wldelft.nl/fews/PI"}
        current_attempt_latest = None
        try:
            root = ET.fromstring(xml_content)
            series_list = root.findall("pi:series", namespace)

            for series_elem in series_list:
                header_elem = series_elem.find("pi:header", namespace)
                if header_elem is not None:
                    last_value_elem = header_elem.find("pi:lastValueTime", namespace)
                    if last_value_elem is not None:
                        # Parse the last value time for this series
                        last_date = last_value_elem.get("date")
                        last_time = last_value_elem.get("time")
                        if last_date and last_time:
                            last_datetime_str = f"{last_date}T{last_time}+00:00"
                            candidate_last_value = datetime.fromisoformat(
                                last_datetime_str
                            )

                            # Keep track of the latest one in this attempt
                            if (
                                current_attempt_latest is None
                                or candidate_last_value > current_attempt_latest
                            ):
                                current_attempt_latest = candidate_last_value

        except Exception:
            pass

        # If we found data in this attempt
        if current_attempt_latest is not None:
            found_data = True

            # Update global latest if this is newer
            if (
                global_latest_last_value is None
                or current_attempt_latest > global_latest_last_value
            ):
                global_latest_last_value = current_attempt_latest
                print(f"Found newer data: {global_latest_last_value}")

            # Move FORWARD to find even more recent data
            current_time += step_back
            step_back = timedelta(days=30)  # Use smaller steps when going forward
        else:
            # No data in this range
            if found_data:
                # We already found data, so move forward to find more recent data
                current_time += step_back
                step_back = timedelta(days=30)  # Use smaller steps when going forward
            else:
                # Haven't found data yet, keep going backward
                current_time -= step_back
                step_back = min(
                    step_back * 1.5, timedelta(days=365)
                )  # Max 1 year steps

    # Return the latest value we found across all attempts
    if global_latest_last_value is not None:
        return global_latest_last_value

    raise ValueError(f"Could not find last value time after {max_attempts} attempts")


def find_first_value_time(
    webservice_url: str,
    parameter_id: str = None,
    location_id: str = None,
    module_instance_id: str = None,
    last_value_time: datetime = None,
    max_attempts: int = 20,
) -> datetime:
    """
    Find the first value time by working backward from the last_value_time.

    This is more efficient than starting from 2000 and moving forward.
    """
    # Use the last_value_time as our starting point, or current time if not provided
    max_end_time = last_value_time if last_value_time else datetime.now(timezone.utc)

    # Start from a reasonable point in the past relative to the last value time
    # This ensures we don't miss recent data while still searching backward
    current_end = max_end_time

    earliest_found = None

    for attempt in range(max_attempts):
        # Work backward from the current end time with smaller steps
        # Use smaller steps to avoid missing data
        step_days = min(
            365, 365 * (attempt + 1) // 5
        )  # Start with 1 year, increase gradually
        current_start = current_end - timedelta(days=step_days)

        # Prevent going too far back
        if current_start < datetime(2000, 1, 1, tzinfo=timezone.utc):
            current_start = datetime(2000, 1, 1, tzinfo=timezone.utc)

        # Prevent invalid time ranges
        if current_start >= current_end:
            break

        error, xml_content, _ = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            module_instance_id=module_instance_id,
            start_time=current_start,
            end_time=current_end,
            show_statistics=True,
            document_format="PI_XML",
        )

        if error or not xml_content:
            # No data in this range, move further back
            current_end = current_start - timedelta(days=1)
            continue

        # Parse XML to check if we have data
        namespace = {"pi": "http://www.wldelft.nl/fews/PI"}
        try:
            root = ET.fromstring(xml_content)
            series_elem = root.find("pi:series", namespace)
            if series_elem is not None:
                header_elem = series_elem.find("pi:header", namespace)
                if header_elem is not None:
                    first_value_elem = header_elem.find("pi:firstValueTime", namespace)
                    if first_value_elem is not None:
                        # Found data! Parse the first value time
                        first_date = first_value_elem.get("date")
                        first_time = first_value_elem.get("time")
                        if first_date and first_time:
                            first_datetime_str = f"{first_date}T{first_time}+00:00"
                            candidate_first = datetime.fromisoformat(first_datetime_str)

                            # Keep track of the earliest we've found
                            if (
                                earliest_found is None
                                or candidate_first < earliest_found
                            ):
                                earliest_found = candidate_first

                            # Continue searching backward to find even earlier data
                            current_end = current_start - timedelta(days=1)
                            continue
        except Exception:
            pass

        # If we get here, no data found, move further back
        current_end = current_start - timedelta(days=1)

    # Return the earliest we found, or do a comprehensive wide-range search
    if earliest_found:
        print(f"Found first value time: {earliest_found}")
        return earliest_found

    # If we found a last_value_time but no first_value_time, do a comprehensive search
    # across a much wider time range (1990-2026) to find the actual data
    print(
        f"Could not find first value time after {max_attempts} attempts, doing wide-range search"
    )
    print(f"Searching wide range from 1990 to 2026 for parameter {parameter_id}")

    # Search across the entire possible range with large steps
    wide_start = datetime(1990, 1, 1, tzinfo=timezone.utc)
    wide_end = datetime(2026, 12, 31, tzinfo=timezone.utc)
    step_days = 365 * 2  # 2 year steps for wide search

    current_wide_start = wide_start
    while current_wide_start < wide_end:
        current_wide_end = min(current_wide_start + timedelta(days=step_days), wide_end)

        print(f"Wide search: {current_wide_start} to {current_wide_end}")

        error, xml_content, _ = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            module_instance_id=module_instance_id,
            start_time=current_wide_start,
            end_time=current_wide_end,
            show_statistics=True,
            document_format="PI_XML",
        )

        if error:
            print(f"API error in wide search: {error}")
            current_wide_start = current_wide_end
            continue

        if not xml_content:
            print("No XML content in wide search")
            current_wide_start = current_wide_end
            continue

        # Parse XML to check if we have data
        namespace = {"pi": "http://www.wldelft.nl/fews/PI"}
        try:
            root = ET.fromstring(xml_content)
            print(f"XML root tag: {root.tag}")
            series_elem = root.find("pi:series", namespace)
            if series_elem is not None:
                print("Found series element")
                header_elem = series_elem.find("pi:header", namespace)
                if header_elem is not None:
                    print("Found header element")

                    # Check for both firstValueTime and lastValueTime
                    first_value_elem = header_elem.find("pi:firstValueTime", namespace)
                    last_value_elem = header_elem.find("pi:lastValueTime", namespace)

                    print(f"firstValueTime: {first_value_elem is not None}")
                    print(f"lastValueTime: {last_value_elem is not None}")

                    if first_value_elem is not None:
                        print(
                            f"Found firstValueTime element: {first_value_elem.attrib}"
                        )
                        # Found data! Parse the first value time
                        first_date = first_value_elem.get("date")
                        first_time = first_value_elem.get("time")
                        if first_date and first_time:
                            first_datetime_str = f"{first_date}T{first_time}+00:00"
                            candidate_first = datetime.fromisoformat(first_datetime_str)

                            print(
                                f"Found first value time in wide search: {candidate_first}"
                            )
                            return candidate_first
                        else:
                            print(
                                f"Missing date/time in firstValueTime: date={first_date}, time={first_time}"
                            )
                    elif last_value_elem is not None:
                        print(
                            f"Found lastValueTime but no firstValueTime: {last_value_elem.attrib}"
                        )
                        # If we have lastValueTime but no firstValueTime, we can't determine the actual range
                        # Skip this series rather than making up dates
                        last_date = last_value_elem.get("date")
                        last_time = last_value_elem.get("time")
                        if last_date and last_time:
                            last_datetime_str = f"{last_date}T{last_time}+00:00"
                            candidate_last = datetime.fromisoformat(last_datetime_str)
                            print(
                                f"Found lastValueTime but no firstValueTime: {candidate_last}"
                            )
                            print(
                                "Skipping this series - cannot determine actual first value time"
                            )
                            return None
                    else:
                        print("No firstValueTime or lastValueTime elements found")
                else:
                    print("No header element found")
            else:
                print("No series element found")
        except Exception as e:
            print(f"XML parsing error: {e}")
            pass

        current_wide_start = current_wide_end

    # If we still can't find anything, this means we can't determine the actual data range
    # Skip this series rather than making up dates
    print(f"No firstValueTime found in any time range for parameter {parameter_id}")
    print("Skipping this series - cannot determine actual data range")

    # Return None to indicate this series should be skipped
    return None


def get_true_data_range(
    webservice_url: str,
    parameter_id: str = None,
    location_id: str = None,
    module_instance_id: str = None,
) -> tuple[datetime, datetime]:
    """
    Find the true data availability range using series-aware iterative search.

    This approach:
    1. Finds all series combinations for the parameter/location
    2. Determines the overall data availability range across all series
    3. Returns the earliest first time and latest last time

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_id: Parameter ID to query for
        location_id: Location ID to query for
        module_instance_id: Module instance ID to filter by

    Returns:
        Tuple of (first_value_time, last_value_time) representing the true data availability range

    Raises:
        ValueError: If unable to determine data range
    """
    print("Finding data range for all series combinations...")

    # Get all series data using the series-aware approach
    series_data = find_series_data_range(
        webservice_url=webservice_url,
        parameter_ids=[parameter_id] if parameter_id else None,
        location_ids=[location_id] if location_id else None,
        module_instance_id=module_instance_id,
    )

    if not series_data:
        raise ValueError(
            f"No series data found for parameter {parameter_id or location_id}"
        )

    # Find the overall range across all series
    earliest_first = None
    latest_last = None

    for series_key, data in series_data.items():
        if data["hasData"] and data["firstValueTime"] and data["lastValueTime"]:
            if earliest_first is None or data["firstValueTime"] < earliest_first:
                earliest_first = data["firstValueTime"]
            if latest_last is None or data["lastValueTime"] > latest_last:
                latest_last = data["lastValueTime"]

    if earliest_first is None or latest_last is None:
        # Fallback: use the old approach if series-aware approach doesn't find data
        print(
            "Series-aware approach found no data, falling back to traditional search..."
        )
    last_value_time = find_last_value_time(
        webservice_url=webservice_url,
        parameter_id=parameter_id,
        location_id=location_id,
        module_instance_id=module_instance_id,
    )
    first_value_time = find_first_value_time(
        webservice_url=webservice_url,
        parameter_id=parameter_id,
        location_id=location_id,
        module_instance_id=module_instance_id,
        last_value_time=last_value_time,
    )

    # If we can't determine the first value time, skip this series
    if first_value_time is None:
        raise ValueError(
            f"Cannot determine data range for parameter {parameter_id} - skipping series"
        )

    return first_value_time, last_value_time
