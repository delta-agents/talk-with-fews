"""
Tests for the get_series_headers functionality.

This module tests the series headers retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
import os
from pydantic_ai import ModelRetry
import pytest
from talk_with_fews.models.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.models.ingest_series_headers import IngestSeriesHeadersOutput
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.webservice.get_series_headers import get_series_headers
from talk_with_fews.tools.webservice.ingest_series_headers import ingest_series_headers
from tests.utils_tests import setup_dot_env
from tests.test_config import get_test_service_config
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
