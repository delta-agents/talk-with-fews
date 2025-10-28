"""
Ingest series headers from FEWS webservice into local DuckDB cache.

This tool fetches series headers from the FEWS webservice and stores them in the local
DuckDB database for incremental caching. Supports both single and bulk ingestion modes.

Modes:
- Single ingestion: parameter-based or location-based queries (original functionality)
- Bulk ingestion: discover and ingest all available series headers (new functionality)
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
import duckdb
import asyncio
import httpx
from datetime import datetime
from pydantic_ai import ModelRetry
from talk_with_fews.models.base import SeriesHeader
from talk_with_fews.models.webservice.ingest_series_headers import (
    IngestSeriesHeadersOutput,
)
from talk_with_fews.utils.webservice_utils import get_timeseries_headers
from talk_with_fews.utils.logging_utils import logger


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
        # Note: We're not storing first_value_time and last_value_time
        # as per user requirements

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
            timeZone=header_elem.get("timeZone", "") or "",  # Ensure string, not None
            qualifiers=qualifiers,
            first_value_time=None,  # Not storing time information
            last_value_time=None,  # Not storing time information
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
            timeStepUnit, timeStepMultiplier, missVal, timeZone, qualifiers
        ) VALUES (nextval('series_headers_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        "SELECT locationId, parameterId, type, timeStepUnit FROM series_headers ORDER BY locationId, parameterId LIMIT 10",
    ]

    return IngestSeriesHeadersOutput(
        description=f"Successfully ingested {inserted_count} series headers for {query_type}",
        series_count=inserted_count,
        sql_examples=sql_examples,
    )


# ============================================================================
# BULK INGESTION FUNCTIONS
# ============================================================================


async def discover_all_series_headers_async(
    webservice_url: str,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    show_statistics: bool = True,
    max_concurrent: int = 20,
) -> Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
    """
    Async version for high-performance parallel processing of series headers discovery.

    Uses httpx.AsyncClient with connection pooling and HTTP/2 support for optimal
    performance when processing many parameters/locations in parallel.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        show_statistics: Whether to include statistics in the response
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Dictionary mapping request_key -> series_data where series_data contains
        all discovered series headers for that request
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

        async def fetch_series_headers(
            request_params: dict,
        ) -> Tuple[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
            """Fetch series headers for given parameters/locations."""
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

                # Parse XML and extract series headers
                series_headers = {}

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
                        module_instance_id_elem = header_elem.find(
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
                            module_instance_id_elem.text
                            if module_instance_id_elem is not None
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

                        # Extract other metadata from header element
                        type_elem = header_elem.find("type") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}type"
                        )
                        series_type = type_elem.text if type_elem is not None else None

                        time_step_elem = header_elem.find(
                            "timeStep"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeStep")
                        time_step_unit = ""
                        time_step_multiplier = 1
                        if time_step_elem is not None:
                            time_step_unit = time_step_elem.get("unit") or ""
                            time_step_multiplier = time_step_elem.get("multiplier")
                            if time_step_multiplier:
                                try:
                                    time_step_multiplier = int(time_step_multiplier)
                                except ValueError:
                                    time_step_multiplier = 1
                            else:
                                time_step_multiplier = 1

                        miss_val_elem = header_elem.find("missVal") or header_elem.find(
                            "{http://www.wldelft.nl/fews/PI}missVal"
                        )
                        miss_val = 0.0
                        if miss_val_elem is not None and miss_val_elem.text:
                            try:
                                miss_val = float(miss_val_elem.text)
                            except ValueError:
                                pass

                        time_zone_elem = header_elem.find(
                            "timeZone"
                        ) or header_elem.find("{http://www.wldelft.nl/fews/PI}timeZone")
                        time_zone = (
                            time_zone_elem.text
                            if time_zone_elem is not None and time_zone_elem.text
                            else ""
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

                        # Store the series header data
                        series_key = (module_instance_id, location_id, parameter_id)
                        series_headers[series_key] = {
                            "type": series_type,
                            "moduleInstanceId": module_instance_id,
                            "locationId": location_id,
                            "parameterId": parameter_id,
                            "timeStepUnit": time_step_unit,
                            "timeStepMultiplier": time_step_multiplier,
                            "missVal": miss_val,
                            "timeZone": time_zone,
                            "qualifiers": qualifiers,
                        }

                except ET.ParseError as e:
                    logger.error(f"Error parsing XML for request {request_params}: {e}")
                    return "error", {}
                except Exception as e:
                    logger.error(
                        f"Error processing series headers for request {request_params}: {e}"
                    )
                    return "error", {}

                # Create a key for the request (either parameter or location based)
                request_key = (
                    "params_" + "_".join(request_params.get("parameter_ids", []))
                    if request_params.get("parameter_ids")
                    else "locs_" + "_".join(request_params.get("location_ids", []))
                )

                logger.info(
                    f"Discovered {len(series_headers)} series headers for {request_key}"
                )
                return request_key, series_headers

            except Exception as e:
                logger.error(f"Error fetching series headers for {request_params}: {e}")
                return "error", {}

        # Process requests with controlled concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(request_params: dict):
            async with semaphore:
                return await fetch_series_headers(request_params)

        # Create request tasks based on what we're processing
        tasks = []

        if parameter_ids:
            # Process each parameter individually for better granularity
            for param_id in parameter_ids:
                tasks.append(fetch_with_semaphore({"parameter_ids": [param_id]}))
        elif location_ids:
            # Process each location individually for better granularity
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

            request_key, series_headers = result
            results[request_key] = series_headers

    return results


def discover_all_series_headers_sync(
    webservice_url: str,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    show_statistics: bool = True,
    max_concurrent: int = 20,
) -> Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]]:
    """
    Synchronous wrapper for the async series headers discovery function.

    This function handles the case where we're already in an event loop
    (like in FastAPI test environments) by using a separate thread.

    Args:
        webservice_url: Base URL of the FEWS webservice
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        show_statistics: Whether to include statistics in the response
        max_concurrent: Maximum number of concurrent requests (default: 20)

    Returns:
        Dictionary mapping request_key -> series_data where series_data contains
        all discovered series headers for that request
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # If we're in an event loop, we need to handle this differently
        import concurrent.futures

        # Run in a separate thread with its own event loop
        def run_in_thread():
            return asyncio.run(
                discover_all_series_headers_async(
                    webservice_url=webservice_url,
                    parameter_ids=parameter_ids,
                    location_ids=location_ids,
                    show_statistics=show_statistics,
                    max_concurrent=max_concurrent,
                )
            )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()

    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(
            discover_all_series_headers_async(
                webservice_url=webservice_url,
                parameter_ids=parameter_ids,
                location_ids=location_ids,
                show_statistics=show_statistics,
                max_concurrent=max_concurrent,
            )
        )


def validate_foreign_keys_batch(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    series_headers: List[SeriesHeader],
) -> List[SeriesHeader]:
    """
    Validate foreign keys for a batch of series headers.

    Args:
        cache_FewsWebServices_db: DuckDB connection for caching
        series_headers: List of SeriesHeader objects to validate

    Returns:
        List of SeriesHeader objects that passed validation
    """
    if not series_headers:
        return []

    # Extract unique location and parameter IDs
    location_ids = list(set(sh.locationId for sh in series_headers))
    parameter_ids = list(set(sh.parameterId for sh in series_headers))

    # Check which locations exist
    location_exists_query = f"""
        SELECT locationId FROM locations
        WHERE locationId IN ({",".join(["?" for _ in location_ids])})
    """
    existing_locations = set(
        row[0]
        for row in cache_FewsWebServices_db.execute(
            location_exists_query, location_ids
        ).fetchall()
    )

    # Check which parameters exist
    parameter_exists_query = f"""
        SELECT id FROM parameters
        WHERE id IN ({",".join(["?" for _ in parameter_ids])})
    """
    existing_parameters = set(
        row[0]
        for row in cache_FewsWebServices_db.execute(
            parameter_exists_query, parameter_ids
        ).fetchall()
    )

    # Filter series headers to only include those with valid foreign keys
    valid_series_headers = []
    invalid_count = 0

    for sh in series_headers:
        if (
            sh.locationId in existing_locations
            and sh.parameterId in existing_parameters
        ):
            valid_series_headers.append(sh)
        else:
            invalid_count += 1
            logger.debug(
                f"Skipping series header - locationId={sh.locationId} exists={sh.locationId in existing_locations}, "
                f"parameterId={sh.parameterId} exists={sh.parameterId in existing_parameters}"
            )

    if invalid_count > 0:
        logger.warning(
            f"Skipped {invalid_count} series headers due to missing foreign keys"
        )

    return valid_series_headers


def deduplicate_series_headers(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    series_headers: List[SeriesHeader],
) -> List[SeriesHeader]:
    """
    Remove series headers that already exist in the database.

    Args:
        cache_FewsWebServices_db: DuckDB connection for caching
        series_headers: List of SeriesHeader objects to check

    Returns:
        List of SeriesHeader objects that don't already exist
    """
    if not series_headers:
        return []

    # Create a list of tuples for checking existing series
    series_keys = [
        (sh.locationId, sh.parameterId, sh.moduleInstanceId) for sh in series_headers
    ]

    # Check which series already exist
    existing_series = set()
    for location_id, parameter_id, module_instance_id in series_keys:
        result = cache_FewsWebServices_db.execute(
            """
            SELECT COUNT(*) FROM series_headers
            WHERE locationId = ? AND parameterId = ? AND moduleInstanceId = ?
            """,
            [location_id, parameter_id, module_instance_id],
        ).fetchone()[0]

        if result > 0:
            existing_series.add((location_id, parameter_id, module_instance_id))

    # Filter out existing series
    new_series_headers = []
    duplicate_count = 0

    for sh in series_headers:
        series_key = (sh.locationId, sh.parameterId, sh.moduleInstanceId)
        if series_key not in existing_series:
            new_series_headers.append(sh)
        else:
            duplicate_count += 1

    if duplicate_count > 0:
        logger.info(f"Skipped {duplicate_count} duplicate series headers")

    return new_series_headers


def insert_series_headers_batch(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    series_headers: List[SeriesHeader],
    batch_size: int = 1000,
) -> int:
    """
    Insert series headers in batches for optimal performance.

    Args:
        cache_FewsWebServices_db: DuckDB connection for caching
        series_headers: List of SeriesHeader objects to insert
        batch_size: Number of series headers to insert per batch

    Returns:
        Number of series headers successfully inserted
    """
    if not series_headers:
        return 0

    total_inserted = 0

    # Process in batches
    for i in range(0, len(series_headers), batch_size):
        batch = series_headers[i : i + batch_size]

        # Prepare batch data for insertion
        batch_data = []
        for sh in batch:
            batch_data.append(
                [
                    sh.id,  # Include the ID
                    sh.type,
                    sh.moduleInstanceId,
                    sh.locationId,
                    sh.parameterId,
                    sh.timeStepUnit,
                    sh.timeStepMultiplier,
                    sh.missVal,
                    sh.timeZone,
                    sh.qualifiers,
                ]
            )

        # Insert batch using DuckDB's batch insertion
        try:
            cache_FewsWebServices_db.executemany(
                """
                INSERT INTO series_headers (
                    id, type, moduleInstanceId, locationId, parameterId,
                    timeStepUnit, timeStepMultiplier, missVal, timeZone, qualifiers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch_data,
            )

            total_inserted += len(batch)
            logger.debug(f"Inserted batch of {len(batch)} series headers")

        except Exception as e:
            logger.error(f"Error inserting batch of series headers: {e}")
            # Continue with next batch instead of failing completely
            continue

    return total_inserted


def convert_discovered_data_to_series_headers(
    discovered_data: Dict[str, Dict[Tuple[str, str, str], Dict[str, Any]]],
    start_id: int = 1,
) -> List[SeriesHeader]:
    """
    Convert discovered series headers data to SeriesHeader objects.

    Args:
        discovered_data: Data from discover_all_series_headers function
        start_id: Starting ID for series headers

    Returns:
        List of SeriesHeader objects
    """
    series_headers = []
    current_id = start_id

    for request_key, series_data in discovered_data.items():
        for (
            module_instance_id,
            location_id,
            parameter_id,
        ), series_info in series_data.items():
            # Convert discovered data to SeriesHeader object
            series_header = SeriesHeader(
                id=current_id,
                type=series_info.get("type", ""),
                moduleInstanceId=module_instance_id,
                locationId=location_id,
                parameterId=parameter_id,
                timeStepUnit=series_info.get("timeStepUnit", ""),
                timeStepMultiplier=series_info.get("timeStepMultiplier")
                or 1,  # Handle None values
                missVal=series_info.get("missVal", 0.0),
                timeZone=series_info.get("timeZone", ""),  # Ensure string, not None
                qualifiers=series_info.get("qualifiers"),
                first_value_time=None,  # Not storing time information
                last_value_time=None,  # Not storing time information
            )
            series_headers.append(series_header)
            current_id += 1

    return series_headers


def ingest_all_series_headers(
    webservice_url: str,
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_ids: List[str] = None,
    location_ids: List[str] = None,
    batch_size: int = 1000,
    max_concurrent: int = 20,
) -> IngestSeriesHeadersOutput:
    """
    Ingest all discovered series headers into local DuckDB cache.

    This function orchestrates the complete process of discovering and ingesting
    all available series headers from the FEWS webservice.

    Args:
        webservice_url: URL of the FEWS webservice
        cache_FewsWebServices_db: DuckDB connection for caching
        parameter_ids: List of parameter IDs to process (optional)
        location_ids: List of location IDs to process (optional)
        batch_size: Number of series headers to insert per batch
        max_concurrent: Maximum number of concurrent requests for discovery

    Returns:
        IngestSeriesHeadersOutput with status and statistics
    """
    logger.info("Starting bulk series headers ingestion")
    start_time = datetime.now()

    try:
        # Step 1: Discover all series headers
        logger.info("Step 1: Discovering all series headers...")
        discovered_data = discover_all_series_headers_sync(
            webservice_url=webservice_url,
            parameter_ids=parameter_ids,
            location_ids=location_ids,
            show_statistics=False,  # No need for statistics since we don't store time info
            max_concurrent=max_concurrent,
        )

        # Count total discovered series headers
        total_discovered = sum(
            len(series_data) for series_data in discovered_data.values()
        )
        logger.info(
            f"Discovered {total_discovered} series headers across {len(discovered_data)} requests"
        )

        if total_discovered == 0:
            return IngestSeriesHeadersOutput(
                description="No series headers discovered",
                series_count=0,
                sql_examples=[],
            )

        # Step 2: Convert to SeriesHeader objects
        logger.info("Step 2: Converting discovered data to SeriesHeader objects...")
        latest_id = cache_FewsWebServices_db.execute(
            "SELECT COALESCE(MAX(id), 0) FROM series_headers"
        ).fetchone()[0]

        series_headers = convert_discovered_data_to_series_headers(
            discovered_data, start_id=latest_id + 1
        )
        logger.info(f"Converted {len(series_headers)} series headers to objects")

        # Step 3: Validate foreign keys
        logger.info("Step 3: Validating foreign keys...")
        valid_series_headers = validate_foreign_keys_batch(
            cache_FewsWebServices_db, series_headers
        )
        logger.info(
            f"Validated {len(valid_series_headers)} series headers with valid foreign keys"
        )

        # Step 4: Remove duplicates
        logger.info("Step 4: Removing duplicates...")
        new_series_headers = deduplicate_series_headers(
            cache_FewsWebServices_db, valid_series_headers
        )
        logger.info(f"Found {len(new_series_headers)} new series headers to insert")

        # Step 5: Insert in batches
        logger.info("Step 5: Inserting series headers in batches...")
        inserted_count = insert_series_headers_batch(
            cache_FewsWebServices_db, new_series_headers, batch_size
        )
        logger.info(f"Successfully inserted {inserted_count} series headers")

        # Bulk ingestion complete
        logger.info("Bulk ingestion completed successfully")

        # Calculate timing
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Generate SQL examples
        sql_examples = [
            "SELECT COUNT(*) FROM series_headers",
            "SELECT COUNT(DISTINCT locationId) FROM series_headers",
            "SELECT COUNT(DISTINCT parameterId) FROM series_headers",
            "SELECT sh.*, l.shortName, p.name FROM series_headers sh JOIN locations l ON sh.locationId = l.locationId JOIN parameters p ON sh.parameterId = p.id LIMIT 5",
            "SELECT locationId, parameterId, type, timeStepUnit FROM series_headers ORDER BY locationId, parameterId LIMIT 10",
        ]

        logger.info(
            f"Bulk series headers ingestion completed in {duration:.2f} seconds"
        )

        return IngestSeriesHeadersOutput(
            description=f"Successfully ingested {inserted_count} series headers in {duration:.2f} seconds",
            series_count=inserted_count,
            sql_examples=sql_examples,
        )

    except Exception as e:
        logger.error(f"Error during bulk series headers ingestion: {e}")
        raise
