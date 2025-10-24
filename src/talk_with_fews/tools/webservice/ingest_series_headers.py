"""
Ingest series headers from FEWS webservice into local DuckDB cache.

This tool fetches series headers from the FEWS webservice and stores them in the local
DuckDB database for incremental caching. Supports both parameter-based and location-based queries.
"""

import xml.etree.ElementTree as ET
from typing import List
import duckdb
from datetime import datetime, timezone, timedelta
from pydantic_ai import ModelRetry
from talk_with_fews.models.base import SeriesHeader
from talk_with_fews.models.webservice.ingest_series_headers import (
    IngestSeriesHeadersOutput,
)
from talk_with_fews.utils.webservice_utils import get_timeseries_headers


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
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection, series_header: SeriesHeader
) -> bool:
    """Insert series header with foreign key validation"""

    # Validate foreign keys before insertion
    if not validate_foreign_keys(
        cache_FewsWebServices_db, series_header.locationId, series_header.parameterId
    ):
        print(
            f"Warning: Foreign key validation failed for locationId={series_header.locationId}, parameterId={series_header.parameterId}"
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
) -> IngestSeriesHeadersOutput:
    """
    Ingest series headers from FEWS webservice into local DuckDB cache.

    Args:
        webservice_url: URL of the FEWS webservice
        cache_FewsWebServices_db: DuckDB connection for caching
        parameter_id: Parameter ID to ingest series headers for
        location_id: Location ID to ingest series headers for

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
        error, data, request_time = get_timeseries_headers(
            webservice_url=webservice_url,
            parameter_id=parameter_id,
            location_id=location_id,
            show_statistics=True,  # Enable statistics to get first/last value times
            document_format="PI_XML",  # Use XML format for proper header discovery with statistics
            # Note: CSV format doesn't respect onlyHeaders=True parameter in this FEWS implementation
            # CSV always returns full time series data, not just headers with statistics
        )

        if error is None and data is None:
            # No data found - this is normal
            return IngestSeriesHeadersOutput(
                description=f"No time series found for {query_type}",
                series_count=0,
                sql_examples=[],
            )

    except ValueError as e:
        # Re-raise with context
        raise ValueError(f"Error fetching series headers for {query_type}: {e}")

    latest_id = cache_FewsWebServices_db.execute(
        "SELECT COALESCE(MAX(id), 0) FROM series_headers"
    ).fetchone()[0]
    start_id = latest_id + 1
    series_headers = parse_series_headers_xml(data, start_id)

    inserted_count = 0
    for series_header in series_headers:
        if insert_series_header(cache_FewsWebServices_db, series_header):
            inserted_count += 1

    # Generate SQL examples
    sql_examples = [
        f"SELECT COUNT(*) FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}'",
        f"SELECT * FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}' LIMIT 5",
        "SELECT sh.*, l.shortName, p.name FROM series_headers sh JOIN locations l ON sh.locationId = l.locationId JOIN parameters p ON sh.parameterId = p.id LIMIT 5",
        "SELECT locationId, parameterId, first_value_time, last_value_time FROM series_headers WHERE first_value_time IS NOT NULL ORDER BY first_value_time DESC LIMIT 10",
    ]

    return IngestSeriesHeadersOutput(
        description=f"Successfully ingested {inserted_count} series headers for {query_type}",
        series_count=inserted_count,
        sql_examples=sql_examples,
    )
