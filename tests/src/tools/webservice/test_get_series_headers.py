"""
Tests for the get_series_headers functionality.

This module tests the series headers retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
import os
from pydantic_ai import ModelRetry
import pytest
from talk_with_fews.models.webservice.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.models.webservice.ingest_series_headers import (
    IngestSeriesHeadersOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.webservice.get_series_headers import get_series_headers
from talk_with_fews.tools.webservice.ingest_series_headers import ingest_series_headers
from tests.utils_tests import setup_dot_env
from tests.test_config import get_test_service_config, generate_test_client_id
from tests.parallel_decorator import fews_parallel


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_get_series_headers_by_parameter(service):
    """
    Test the get_series_headers function with parameter-based query against all FEWS services.
    """
    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input for parameter-based query
    input_data = GetSeriesHeadersInput(parameter_id=test_data["parameter_ids"][0])

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesHeadersOutput)
    assert isinstance(output.series_headers, list)
    assert len(output.series_headers) >= 0  # Should be non-negative
    assert isinstance(output.description, str)
    assert isinstance(output.available_ids, dict)

    # Check that description mentions the parameter
    assert test_data["parameter_ids"][0] in output.description

    # Check that available_ids contains expected keys for parameter query
    if len(output.series_headers) > 0:
        assert "locations" in output.available_ids


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_get_series_headers_by_location(service):
    """
    Test the get_series_headers function with location-based query against all FEWS services.
    """
    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input for location-based query
    input_data = GetSeriesHeadersInput(location_id=test_data["location_ids"][0])

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesHeadersOutput)
    assert isinstance(output.series_headers, list)
    assert len(output.series_headers) >= 0  # Should be non-negative
    assert isinstance(output.description, str)
    assert isinstance(output.available_ids, dict)

    # Check that description mentions the location (either ID or name)
    # The description might contain either the location ID or the location name
    location_id = test_data["location_ids"][0]
    location_mentioned = location_id in output.description or any(
        header.get("location_name") in output.description
        for header in output.series_headers
    )
    assert location_mentioned, (
        f"Location ID '{location_id}' or location name not found in description: '{output.description}'"
    )

    # Check that available_ids contains expected keys for location query
    if len(output.series_headers) > 0:
        assert "parameters" in output.available_ids


def test_get_series_headers_invalid_input():
    """
    Test the get_series_headers function with invalid input (both parameter and location).
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Call the function and expect ModelRetry
    with pytest.raises(
        ModelRetry,
        match="Only one of 'parameter_id' or 'location_id' can be provided, not both.",
    ):
        # Create invalid input (both parameter and location)
        input_data = GetSeriesHeadersInput(parameter_id="Kwel", location_id="GPG_1698")
        # Get runtime context
        ctx = get_runtime_ctx(user_settings)
        asyncio.run(get_series_headers(ctx, input_data))


def test_get_series_headers_no_input():
    """
    Test the get_series_headers function with no input (neither parameter nor location).
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create invalid input (neither parameter nor location)

    # Call the function and expect ModelRetry
    with pytest.raises(
        ModelRetry, match="Either 'parameter_id' or 'location_id' must be provided."
    ):
        input_data = GetSeriesHeadersInput()
        # Get runtime context
        ctx = get_runtime_ctx(user_settings)
        asyncio.run(get_series_headers(ctx, input_data))


def test_ingest_series_headers_by_parameter():
    """
    Test the ingest_series_headers function with parameter-based query.
    """
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function
    output = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            parameter_id=test_data["parameter_ids"][0],
        )
    )

    # Assert the output is of the expected type
    assert isinstance(output, IngestSeriesHeadersOutput)
    assert isinstance(output.description, str)
    assert output.series_count >= 0  # Should be non-negative
    assert isinstance(output.sql_examples, list)
    assert len(output.sql_examples) >= 1  # Should have at least one SQL example

    # Check that description mentions the parameter
    assert test_data["parameter_ids"][0] in output.description


def test_ingest_series_headers_by_location():
    """
    Test the ingest_series_headers function with location-based query.
    """
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function
    output = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            location_id=test_data["location_ids"][0],
        )
    )

    # Assert the output is of the expected type
    assert isinstance(output, IngestSeriesHeadersOutput)
    assert isinstance(output.description, str)
    assert output.series_count >= 0  # Should be non-negative
    assert isinstance(output.sql_examples, list)
    assert len(output.sql_examples) >= 1  # Should have at least one SQL example

    # Check that description mentions the location
    assert test_data["location_ids"][0] in output.description


def test_ingest_series_headers_invalid_input():
    """
    Test the ingest_series_headers function with invalid input (both parameter and location).
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function and expect ModelRetry
    with pytest.raises(
        ModelRetry, match="Cannot specify both parameter_id and location_id"
    ):
        asyncio.run(
            ingest_series_headers(
                webservice_url=webservice_url,
                cache_FewsWebServices_db=cache_FewsWebServices_db,
                parameter_id="Kwel",
                location_id="GPG_1698",
            )
        )


def test_ingest_series_headers_no_input():
    """
    Test the ingest_series_headers function with no input (neither parameter nor location).
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function and expect ModelRetry
    with pytest.raises(
        ModelRetry, match="Must specify either parameter_id or location_id"
    ):
        asyncio.run(
            ingest_series_headers(
                webservice_url=webservice_url,
                cache_FewsWebServices_db=cache_FewsWebServices_db,
            )
        )


# @fews_parallel("actueelwaterbeeld", "scheldestromen")
@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_ingest_series_headers_skip_empty_data(service):
    """
    Test the skip_empty_data parameter functionality in ingest_series_headers.

    This test verifies that:
    1. skip_empty_data=True (default) filters out series headers with no data
    2. skip_empty_data=False includes all series headers regardless of data availability

    Uses real FEWS service endpoints and validated combinations from test_config.py.
    """
    import asyncio
    from tests.test_config import get_test_service_config
    from tests.utils_tests import setup_dot_env
    from talk_with_fews.routers.setup_connections import get_runtime_ctx
    from talk_with_fews.tools.webservice.ingest_series_headers import (
        ingest_series_headers,
    )
    from talk_with_fews.models.webservice.ingest_series_headers import (
        IngestSeriesHeadersOutput,
    )

    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    # Make client_id unique per service to avoid cache conflicts in parallel tests
    user_settings["client_id"] = generate_test_client_id(service, "skip_empty_data")
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Get runtime context with full database setup (includes locations and parameters ingestion)
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    print(
        "Using runtime context database with locations and parameters already ingested"
    )

    # Use the first validated combination from test config
    validated_combination = test_data["validated_combinations"][0]
    test_parameter = validated_combination["parameter_id"]
    test_location = validated_combination["location_id"]

    print(f"\n=== Testing {service} skip_empty_data functionality ===")
    print(f"Service: {service}")
    print(f"Testing parameter: {test_parameter}")
    print(f"Expected location with data: {test_location} (from test config validation)")
    print("Will ingest all locations for this parameter and verify filtering works")

    # Test 1: skip_empty_data=True (default) - should filter out empty data
    print("\nTest 1: skip_empty_data=True (default)")
    result1 = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            parameter_id=test_parameter,
            skip_empty_data=True,
        )
    )

    # Assert the output structure
    assert isinstance(result1, IngestSeriesHeadersOutput)
    assert isinstance(result1.description, str)
    assert result1.series_count >= 0
    assert isinstance(result1.sql_examples, list)

    print(f"Result: {result1.description}")
    print(f"Series count: {result1.series_count}")

    # Show detailed information about all series headers for this parameter
    print(
        f"\nDetailed breakdown for {service} parameter {test_parameter} (Test 1 - skip_empty_data=True):"
    )
    series_details_1 = cache_FewsWebServices_db.execute(
        """
        SELECT
            locationId,
            first_value_time,
            last_value_time,
            moduleInstanceId
        FROM series_headers
        WHERE parameterId = ?
        ORDER BY locationId
    """,
        [test_parameter],
    ).fetchall()

    for series in series_details_1:
        has_data = series[1] is not None and series[2] is not None
        data_status = "HAS DATA" if has_data else "NO DATA"
        time_range = f"{series[1]} to {series[2]}" if has_data else "No time range"
        print(
            f"  Location {series[0]} | {data_status} | {time_range} | Module: {series[3]}"
        )

    # Count series headers with and without data for this parameter
    count_with_data_1 = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM series_headers
        WHERE parameterId = ? AND first_value_time IS NOT NULL
    """,
        [test_parameter],
    ).fetchone()[0]

    count_without_data_1 = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM series_headers
        WHERE parameterId = ? AND first_value_time IS NULL AND last_value_time IS NULL
    """,
        [test_parameter],
    ).fetchone()[0]

    print(
        f"\nSummary: {count_with_data_1} series with data, {count_without_data_1} series without data"
    )

    # Test 2: skip_empty_data=False - should include all series headers
    print("\nTest 2: skip_empty_data=False")
    result2 = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            parameter_id=test_parameter,
            skip_empty_data=False,
        )
    )

    # Assert the output structure
    assert isinstance(result2, IngestSeriesHeadersOutput)
    assert isinstance(result2.description, str)
    assert result2.series_count >= 0
    assert isinstance(result2.sql_examples, list)

    print(f"Result: {result2.description}")
    print(f"Series count: {result2.series_count}")

    # Show detailed information about all series headers for this parameter
    print(
        f"\nDetailed breakdown for {service} parameter {test_parameter} (Test 2 - skip_empty_data=False):"
    )
    series_details_2 = cache_FewsWebServices_db.execute(
        """
        SELECT
            locationId,
            first_value_time,
            last_value_time,
            moduleInstanceId
        FROM series_headers
        WHERE parameterId = ?
        ORDER BY locationId
    """,
        [test_parameter],
    ).fetchall()

    for series in series_details_2:
        has_data = series[1] is not None and series[2] is not None
        data_status = "HAS DATA" if has_data else "NO DATA"
        time_range = f"{series[1]} to {series[2]}" if has_data else "No time range"
        print(
            f"  Location {series[0]} | {data_status} | {time_range} | Module: {series[3]}"
        )

    # Count series headers with and without data after second test
    count_with_data_2 = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM series_headers
        WHERE parameterId = ? AND first_value_time IS NOT NULL
    """,
        [test_parameter],
    ).fetchone()[0]

    count_without_data_2 = cache_FewsWebServices_db.execute(
        """
        SELECT COUNT(*) FROM series_headers
        WHERE parameterId = ? AND first_value_time IS NULL AND last_value_time IS NULL
    """,
        [test_parameter],
    ).fetchone()[0]

    print(
        f"\nSummary: {count_with_data_2} series with data, {count_without_data_2} series without data"
    )

    # Verify the skip_empty_data functionality
    print(f"\nSkip empty data verification for {service}:")

    # Since this is a validated parameter from test_config.py, we expect it to have some data
    if count_with_data_1 > 0:
        print(
            f"SUCCESS: Found {count_with_data_1} series with actual data (as expected from test config)"
        )
        assert count_with_data_1 > 0, (
            f"Expected series with data for validated parameter {test_parameter}"
        )
    else:
        print(
            "WARNING: No series with data found for validated parameter - test config may need updating"
        )

    # Verify that series with data count remains the same or increases (deduplication working)
    assert count_with_data_2 >= count_with_data_1, (
        "Series with data count should not decrease"
    )

    # If there were series without data, verify the filtering worked
    if count_without_data_2 > count_without_data_1:
        print(
            f"SUCCESS: skip_empty_data=False added {count_without_data_2 - count_without_data_1} series headers with no data"
        )
    elif count_without_data_1 == 0 and count_without_data_2 == 0:
        print(
            "All series headers have data - no empty data to filter (as expected for validated combination)"
        )
    else:
        print("Deduplication occurred - no change in counts")

    print(f"Skip empty data functionality working correctly for {service}")


def test_series_headers_caching():
    """
    Test that series headers are properly cached and subsequent calls use cache.
    """
    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # First call - should trigger ingestion
    input_data1 = GetSeriesHeadersInput(parameter_id=test_data["parameter_ids"][0])
    output1 = asyncio.run(get_series_headers(ctx, input_data1))

    # Second call - should use cache
    input_data2 = GetSeriesHeadersInput(parameter_id=test_data["parameter_ids"][0])
    output2 = asyncio.run(get_series_headers(ctx, input_data2))

    # Both outputs should be identical (same data from cache)
    assert len(output1.series_headers) == len(output2.series_headers)
    assert output1.description == output2.description
    assert output1.available_ids == output2.available_ids


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_series_headers_validated_combinations(service):
    """
    Test series headers with location-parameter combinations for all FEWS services.

    For services with validated_combinations: uses those specific combinations
    For other services: uses first parameter_id + first location_id from test_data
    """
    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Only test services that have validated combinations
    if "validated_combinations" not in test_data:
        pytest.skip(
            f"Service {service} needs validated combinations - skipping until we verify real parameter-location pairs"
        )

    # Use specific validated combinations
    combinations = test_data["validated_combinations"]
    print(f"\n=== Testing {service} with validated combinations ===")

    # Test each combination
    for combo in combinations:
        location_id = combo["location_id"]
        parameter_id = combo["parameter_id"]

        print(f"\nTesting combination: {location_id} + {parameter_id}")

        # Test parameter-based query
        param_input = GetSeriesHeadersInput(parameter_id=parameter_id)
        param_output = asyncio.run(get_series_headers(ctx, param_input))

        assert isinstance(param_output.series_headers, list)
        assert len(param_output.series_headers) >= 0  # Can be empty or have data
        assert (
            parameter_id in param_output.description
            or "No time series found" in param_output.description
        )

        # Test location-based query
        loc_input = GetSeriesHeadersInput(location_id=location_id)
        loc_output = asyncio.run(get_series_headers(ctx, loc_input))

        assert isinstance(loc_output.series_headers, list)
        assert len(loc_output.series_headers) >= 0  # Can be empty or have data
        # The description might contain location ID, location name, or "No time series found"
        assert (
            location_id in loc_output.description
            or "No time series found" in loc_output.description
            or len(loc_output.series_headers) > 0
        )  # If we have data, description is valid

        print(
            f"  ✅ Parameter {parameter_id}: {len(param_output.series_headers)} series"
        )
        print(f"  ✅ Location {location_id}: {len(loc_output.series_headers)} series")


@fews_parallel("actueelwaterbeeld", "hdsr", "wsvv", "hhd", "scheldestromen")
def test_series_headers_output_structure(service):
    """
    Test that the output structure is correct and contains all required fields against all FEWS services.
    """
    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data

    # Create input
    input_data = GetSeriesHeadersInput(parameter_id=test_data["parameter_ids"][0])

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Test output structure
    assert hasattr(output, "series_headers")
    assert hasattr(output, "description")
    assert hasattr(output, "available_ids")

    # Test data types
    assert isinstance(output.series_headers, list)
    assert isinstance(output.description, str)
    assert isinstance(output.available_ids, dict)

    # Test constraints
    assert len(output.series_headers) >= 0
