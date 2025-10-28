"""
Bulk ingestion of all discovered series headers into local DuckDB cache.

This module provides efficient bulk processing of series headers discovered by
the discover_all_series_headers module. It handles batch insertion, validation,
and updates the tracking flags in locations and parameters tables.
"""

import duckdb
from datetime import datetime
from typing import Dict, List, Any, Tuple
from talk_with_fews.models.base import SeriesHeader
from talk_with_fews.models.webservice.ingest_series_headers import (
    IngestSeriesHeadersOutput,
)
from talk_with_fews.utils.logging_utils import logger


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
        # Import here to avoid circular imports
        from talk_with_fews.tools.webservice.discover_all_series_headers import (
            discover_all_series_headers_sync,
        )

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
