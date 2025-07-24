"""
Ingest series headers from FEWS webservice into local DuckDB cache.

This tool fetches series headers from the FEWS webservice and stores them in the local
DuckDB database for incremental caching. Supports both parameter-based and location-based queries.
"""

import xml.etree.ElementTree as ET
from typing import List
import duckdb
from talk_with_fews.models.base import SeriesHeader
from talk_with_fews.models.ingest_series_headers import IngestSeriesHeadersOutput
from talk_with_fews.utils.webservice_utils import get_request


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


def parse_series_headers_xml(xml_content: str) -> List[SeriesHeader]:
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
        time_step_multiplier = (
            int(time_step_elem.get("multiplier")) if time_step_elem is not None else 1
        )

        # Extract qualifiers
        qualifiers_elem = header_elem.find("pi:qualifiers", namespace)
        qualifiers = qualifiers_elem.text if qualifiers_elem is not None else None

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
            id=len(series_headers) + 1,  # Simple auto-increment for now
            type=series_type,
            moduleInstanceId=module_instance_id,
            locationId=location_id,
            parameterId=parameter_id,
            timeStepUnit=time_step_unit or "",
            timeStepMultiplier=time_step_multiplier,
            missVal=float(header_elem.get("missVal", 0)),
            timeZone=header_elem.get("timeZone", ""),
            qualifiers=qualifiers,
        )

        series_headers.append(series_header)

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
            timeStepUnit, timeStepMultiplier, missVal, timeZone, qualifiers
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        [
            series_header.id,
            series_header.type,
            series_header.moduleInstanceId,
            series_header.locationId,
            series_header.parameterId,
            series_header.timeStepUnit,
            series_header.timeStepMultiplier,
            series_header.missVal,
            series_header.timeZone,
            series_header.qualifiers,
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
        raise ValueError("Cannot specify both parameter_id and location_id")
    if not parameter_id and not location_id:
        raise ValueError("Must specify either parameter_id or location_id")

    # Construct webservice URL
    if parameter_id:
        request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
        params = {
            "parameterIds": parameter_id,
            "onlyHeaders": "True",
            "documentFormat": "PI_XML",
        }
        query_type = f"parameter {parameter_id}"
    else:
        request_url = f"{webservice_url}/rest/fewspiservice/v1/timeseries"
        params = {
            "locationIds": location_id,
            "onlyHeaders": "True",
            "documentFormat": "PI_XML",
        }
        query_type = f"location {location_id}"

    # Fetch data from webservice
    error, data = get_request(request_url, params=params)
    if error is not None:
        raise ValueError(f"Error fetching series headers for {query_type}: {error}")

    # Parse XML and extract series headers
    series_headers = parse_series_headers_xml(data)

    # Insert series headers into database
    inserted_count = 0
    for series_header in series_headers:
        if insert_series_header(cache_FewsWebServices_db, series_header):
            inserted_count += 1

    # Generate SQL examples
    sql_examples = [
        f"SELECT COUNT(*) FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}'",
        f"SELECT * FROM series_headers WHERE {'parameterId' if parameter_id else 'locationId'} = '{parameter_id or location_id}' LIMIT 5",
        "SELECT sh.*, l.shortName, p.name FROM series_headers sh JOIN locations l ON sh.locationId = l.locationId JOIN parameters p ON sh.parameterId = p.id LIMIT 5",
    ]

    return IngestSeriesHeadersOutput(
        description=f"Successfully ingested {inserted_count} series headers for {query_type}",
        series_count=inserted_count,
        sql_examples=sql_examples,
    )
