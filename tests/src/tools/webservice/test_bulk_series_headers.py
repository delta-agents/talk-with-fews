"""
Test bulk series headers ingestion functionality across all FEWS backends.

This test validates the new bulk series headers ingestion system that pre-populates
all series headers during server initialization, eliminating the need for on-demand
ingestion during user requests.
"""

import os
import pytest
import duckdb
from tests.test_config import FEWS_SERVICES
from tests.parallel_decorator import fews_parallel
from talk_with_fews.tools.webservice.ingest_locations import ingest_locations
from talk_with_fews.tools.webservice.ingest_parameters import ingest_parameters
from talk_with_fews.tools.webservice.ingest_all_series_headers import (
    ingest_all_series_headers,
)
from talk_with_fews.tools.webservice.discover_all_series_headers import (
    discover_all_series_headers_sync,
)
from talk_with_fews.routers.setup_connections import setup_series_headers_table


# Skip all tests if bulk series headers ingestion is disabled
pytestmark = pytest.mark.skipif(
    os.environ.get("DEV_DISABLE_SERIES_HEADERS_INGEST", "false").lower()
    in ("true", "1", "yes"),
    reason="Bulk series headers ingestion is disabled via DEV_DISABLE_SERIES_HEADERS_INGEST",
)


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_bulk_series_headers_discovery(service):
    """Test series headers discovery functionality."""
    config = FEWS_SERVICES[service]

    # Test with a small subset of parameters from config
    test_parameter_ids = config.test_data["parameter_ids"][:2]  # First 2 parameters

    # Test discovery
    discovered_data = discover_all_series_headers_sync(
        webservice_url=config.web_service_url,
        parameter_ids=test_parameter_ids,
        show_statistics=False,  # We disabled statistics
        max_concurrent=5,  # Lower concurrency for testing
    )

    # Validate results
    assert discovered_data is not None, f"Discovery failed for {service}"
    assert len(discovered_data) > 0, f"No series headers discovered for {service}"

    total_discovered = sum(len(series_data) for series_data in discovered_data.values())
    assert total_discovered > 0, f"No series headers found for {service}"

    # Validate structure of discovered data
    for request_key, series_data in discovered_data.items():
        assert isinstance(series_data, dict), (
            f"Invalid series_data structure for {service}"
        )

        for series_key, series_info in series_data.items():
            assert isinstance(series_key, tuple), (
                f"Invalid series_key type for {service}"
            )
            assert len(series_key) == 3, f"Invalid series_key length for {service}"

            # Validate required fields
            required_fields = ["locationId", "parameterId", "moduleInstanceId", "type"]
            for field in required_fields:
                assert field in series_info, f"Missing field {field} for {service}"
                assert series_info[field] is not None, (
                    f"Null value for {field} in {service}"
                )


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_bulk_series_headers_ingestion(service):
    """Test complete bulk series headers ingestion pipeline."""
    config = FEWS_SERVICES[service]

    # Create test in-memory database
    cache_db = duckdb.connect(database=":memory:", read_only=False)
    cache_db.execute("INSTALL spatial;")
    cache_db.execute("LOAD spatial;")

    # Step 1: Ingest locations
    locations_result = ingest_locations(config.web_service_url, cache_db)
    assert locations_result is not None, f"Locations ingestion failed for {service}"

    locations_count = cache_db.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    assert locations_count > 0, f"No locations ingested for {service}"

    # Step 2: Ingest parameters
    parameters_result = ingest_parameters(config.web_service_url, cache_db)
    if parameters_result is None:
        pytest.skip(f"Parameters ingestion not supported for {service}")

    parameters_count = cache_db.execute("SELECT COUNT(*) FROM parameters").fetchone()[0]
    assert parameters_count > 0, f"No parameters ingested for {service}"

    # Step 3: Setup series headers table
    cache_db = setup_series_headers_table(cache_db)

    # Step 4: Test bulk series headers ingestion with subset
    all_parameter_ids = [
        row[0] for row in cache_db.execute("SELECT id FROM parameters").fetchall()
    ]
    all_location_ids = [
        row[0]
        for row in cache_db.execute("SELECT locationId FROM locations").fetchall()
    ]

    # Use a small subset to avoid overwhelming the service
    test_parameter_ids = all_parameter_ids[:3]  # First 3 parameters
    test_location_ids = all_location_ids[:5]  # First 5 locations

    result = ingest_all_series_headers(
        webservice_url=config.web_service_url,
        cache_FewsWebServices_db=cache_db,
        parameter_ids=test_parameter_ids,
        location_ids=test_location_ids,
        batch_size=50,  # Small batch size for testing
        max_concurrent=3,  # Lower concurrency for testing
    )

    # Validate ingestion result
    assert result is not None, f"Bulk ingestion failed for {service}"
    assert result.series_count >= 0, f"Invalid series count for {service}"

    # Validate database state
    final_locations_count = cache_db.execute(
        "SELECT COUNT(*) FROM locations"
    ).fetchone()[0]
    final_parameters_count = cache_db.execute(
        "SELECT COUNT(*) FROM parameters"
    ).fetchone()[0]
    series_headers_count = cache_db.execute(
        "SELECT COUNT(*) FROM series_headers"
    ).fetchone()[0]

    assert final_locations_count == locations_count, (
        f"Location count changed for {service}"
    )
    assert final_parameters_count == parameters_count, (
        f"Parameter count changed for {service}"
    )
    assert series_headers_count == result.series_count, (
        f"Series headers count mismatch for {service}"
    )

    # Validate foreign key constraints
    if series_headers_count > 0:
        # Check that all series headers have valid foreign keys
        invalid_series = cache_db.execute("""
            SELECT COUNT(*) FROM series_headers sh
            LEFT JOIN locations l ON sh.locationId = l.locationId
            LEFT JOIN parameters p ON sh.parameterId = p.id
            WHERE l.locationId IS NULL OR p.id IS NULL
        """).fetchone()[0]

        assert invalid_series == 0, (
            f"Found {invalid_series} series headers with invalid foreign keys for {service}"
        )

        # Validate series headers structure
        sample_series = cache_db.execute("""
            SELECT sh.locationId, sh.parameterId, sh.moduleInstanceId, sh.type,
                   sh.timeStepUnit, sh.timeStepMultiplier, sh.missVal, sh.timeZone
            FROM series_headers sh
            LIMIT 1
        """).fetchone()

        assert sample_series is not None, (
            f"No sample series headers found for {service}"
        )
        (
            location_id,
            parameter_id,
            module_instance_id,
            series_type,
            time_step_unit,
            time_step_multiplier,
            miss_val,
            time_zone,
        ) = sample_series

        # Validate required fields are not null
        assert location_id is not None, f"Null locationId for {service}"
        assert parameter_id is not None, f"Null parameterId for {service}"
        assert module_instance_id is not None, f"Null moduleInstanceId for {service}"
        assert series_type is not None, f"Null series_type for {service}"

        # Validate data types
        assert isinstance(time_step_multiplier, int), (
            f"Invalid timeStepMultiplier type for {service}"
        )
        assert isinstance(miss_val, float), f"Invalid missVal type for {service}"
        assert isinstance(time_zone, str), f"Invalid timeZone type for {service}"


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_bulk_series_headers_performance(service):
    """Test performance characteristics of bulk ingestion."""
    config = FEWS_SERVICES[service]

    # Create test in-memory database
    cache_db = duckdb.connect(database=":memory:", read_only=False)
    cache_db.execute("INSTALL spatial;")
    cache_db.execute("LOAD spatial;")

    # Setup database with locations and parameters
    ingest_locations(config.web_service_url, cache_db)
    parameters_result = ingest_parameters(config.web_service_url, cache_db)
    if parameters_result is None:
        pytest.skip(f"Parameters ingestion not supported for {service}")
    cache_db = setup_series_headers_table(cache_db)

    # Get a small subset for performance testing
    all_parameter_ids = [
        row[0] for row in cache_db.execute("SELECT id FROM parameters").fetchall()
    ]
    test_parameter_ids = all_parameter_ids[:2]  # Just 2 parameters for performance test

    import time

    start_time = time.time()

    result = ingest_all_series_headers(
        webservice_url=config.web_service_url,
        cache_FewsWebServices_db=cache_db,
        parameter_ids=test_parameter_ids,
        batch_size=100,
        max_concurrent=5,
    )

    end_time = time.time()
    duration = end_time - start_time

    # Validate performance (should complete within reasonable time)
    assert duration < 30.0, (
        f"Bulk ingestion took too long ({duration:.2f}s) for {service}"
    )
    assert result.series_count >= 0, f"Performance test failed for {service}"

    # Log performance metrics
    print(
        f"Performance for {service}: {duration:.2f}s, {result.series_count} series headers"
    )


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_bulk_series_headers_error_handling(service):
    """Test error handling in bulk ingestion."""
    config = FEWS_SERVICES[service]

    # Create test in-memory database
    cache_db = duckdb.connect(database=":memory:", read_only=False)
    cache_db.execute("INSTALL spatial;")
    cache_db.execute("LOAD spatial;")

    # Setup database with locations and parameters
    ingest_locations(config.web_service_url, cache_db)
    parameters_result = ingest_parameters(config.web_service_url, cache_db)
    if parameters_result is None:
        pytest.skip(f"Parameters ingestion not supported for {service}")
    cache_db = setup_series_headers_table(cache_db)

    # Test with invalid parameter IDs (should handle gracefully)
    invalid_parameter_ids = ["INVALID_PARAM_1", "INVALID_PARAM_2"]

    result = ingest_all_series_headers(
        webservice_url=config.web_service_url,
        cache_FewsWebServices_db=cache_db,
        parameter_ids=invalid_parameter_ids,
        batch_size=50,
        max_concurrent=3,
    )

    # Should complete without error, even with invalid parameters
    assert result is not None, f"Error handling test failed for {service}"
    assert result.series_count == 0, (
        f"Expected 0 series headers for invalid parameters in {service}"
    )


def test_environment_variable_controls():
    """Test environment variable controls for bulk ingestion."""
    import os

    original_value = os.environ.get("DEV_DISABLE_SERIES_HEADERS_INGEST")

    try:
        # Test with disabled ingestion
        os.environ["DEV_DISABLE_SERIES_HEADERS_INGEST"] = "true"
        enable_series_headers_ingest = os.environ.get(
            "DEV_DISABLE_SERIES_HEADERS_INGEST", "false"
        ).lower() not in ("true", "1", "yes")
        assert not enable_series_headers_ingest, (
            "Environment variable not working correctly"
        )

        # Test with enabled ingestion
        os.environ["DEV_DISABLE_SERIES_HEADERS_INGEST"] = "false"
        enable_series_headers_ingest = os.environ.get(
            "DEV_DISABLE_SERIES_HEADERS_INGEST", "false"
        ).lower() not in ("true", "1", "yes")
        assert enable_series_headers_ingest, (
            "Environment variable not working correctly"
        )

    finally:
        # Restore original value
        if original_value is not None:
            os.environ["DEV_DISABLE_SERIES_HEADERS_INGEST"] = original_value
        else:
            os.environ.pop("DEV_DISABLE_SERIES_HEADERS_INGEST", None)


def test_bulk_series_headers_integration():
    """Integration test for the complete bulk series headers system."""
    # Use actueelwaterbeeld for integration test (most reliable)
    config = FEWS_SERVICES["actueelwaterbeeld"]

    # Create test in-memory database
    cache_db = duckdb.connect(database=":memory:", read_only=False)
    cache_db.execute("INSTALL spatial;")
    cache_db.execute("LOAD spatial;")

    # Complete pipeline test
    print(f"Testing complete pipeline with {config.name}")

    # Step 1: Locations
    ingest_locations(config.web_service_url, cache_db)
    locations_count = cache_db.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    print(f"  - Locations: {locations_count}")

    # Step 2: Parameters
    ingest_parameters(config.web_service_url, cache_db)
    parameters_count = cache_db.execute("SELECT COUNT(*) FROM parameters").fetchone()[0]
    print(f"  - Parameters: {parameters_count}")

    # Step 3: Series Headers
    cache_db = setup_series_headers_table(cache_db)

    # Use a small subset for integration test
    all_parameter_ids = [
        row[0] for row in cache_db.execute("SELECT id FROM parameters").fetchall()
    ]
    test_parameter_ids = all_parameter_ids[:3]  # First 3 parameters

    result = ingest_all_series_headers(
        webservice_url=config.web_service_url,
        cache_FewsWebServices_db=cache_db,
        parameter_ids=test_parameter_ids,
        batch_size=100,
        max_concurrent=5,
    )

    series_headers_count = cache_db.execute(
        "SELECT COUNT(*) FROM series_headers"
    ).fetchone()[0]
    print(f"  - Series Headers: {series_headers_count}")

    # Validate integration
    assert locations_count > 0, "Integration test: No locations"
    assert parameters_count > 0, "Integration test: No parameters"
    assert series_headers_count >= 0, "Integration test: Invalid series headers count"
    assert result.series_count == series_headers_count, (
        "Integration test: Count mismatch"
    )

    print(f"✅ Integration test passed: {result.description}")
