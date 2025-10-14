"""
Tests for the get_series_headers functionality.

This module tests the series headers retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
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


def test_get_series_headers_by_parameter():
    """
    Test the get_series_headers function with parameter-based query.
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create input for parameter-based query
    input_data = GetSeriesHeadersInput(parameter_id="Kwel")

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesHeadersOutput)
    assert output.count >= 0  # Should be non-negative
    assert isinstance(output.summary, str)
    assert len(output.summary) <= 200  # Check summary length constraint
    assert isinstance(output.sample_ids, str)
    assert isinstance(output.available_filters, dict)
    assert isinstance(output.follow_up_suggestions, list)

    # Check that summary mentions the parameter
    assert "Kwel" in output.summary

    # Check that available_filters contains expected keys for parameter query
    if output.count > 0:
        assert "locations" in output.available_filters
        assert "model_types" in output.available_filters


def test_get_series_headers_by_location():
    """
    Test the get_series_headers function with location-based query.
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create input for location-based query
    # input_data = GetSeriesHeadersInput(location_id="GPG_1698")
    input_data = GetSeriesHeadersInput(location_id="WS000323")

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesHeadersOutput)
    assert output.count >= 0  # Should be non-negative
    assert isinstance(output.summary, str)
    assert len(output.summary) <= 200  # Check summary length constraint
    assert isinstance(output.sample_ids, str)
    assert isinstance(output.available_filters, dict)
    assert isinstance(output.follow_up_suggestions, list)

    # Check that summary mentions the location
    assert "GPG_1698" in output.summary

    # Check that available_filters contains expected keys for location query
    if output.count > 0:
        assert "parameters" in output.available_filters
        assert "model_types" in output.available_filters


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

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function
    output = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            parameter_id="Kwel",
        )
    )

    # Assert the output is of the expected type
    assert isinstance(output, IngestSeriesHeadersOutput)
    assert isinstance(output.description, str)
    assert output.series_count >= 0  # Should be non-negative
    assert isinstance(output.sql_examples, list)
    assert len(output.sql_examples) >= 1  # Should have at least one SQL example

    # Check that description mentions the parameter
    assert "Kwel" in output.description


def test_ingest_series_headers_by_location():
    """
    Test the ingest_series_headers function with location-based query.
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)
    webservice_url = ctx.deps.webservice_url
    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Call the function
    output = asyncio.run(
        ingest_series_headers(
            webservice_url=webservice_url,
            cache_FewsWebServices_db=cache_FewsWebServices_db,
            location_id="GPG_1698",
        )
    )

    # Assert the output is of the expected type
    assert isinstance(output, IngestSeriesHeadersOutput)
    assert isinstance(output.description, str)
    assert output.series_count >= 0  # Should be non-negative
    assert isinstance(output.sql_examples, list)
    assert len(output.sql_examples) >= 1  # Should have at least one SQL example

    # Check that description mentions the location
    assert "GPG_1698" in output.description


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

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # First call - should trigger ingestion
    input_data1 = GetSeriesHeadersInput(parameter_id="Kwel")
    output1 = asyncio.run(get_series_headers(ctx, input_data1))

    # Second call - should use cache
    input_data2 = GetSeriesHeadersInput(parameter_id="Kwel")
    output2 = asyncio.run(get_series_headers(ctx, input_data2))

    # Both outputs should be identical (same data from cache)
    assert output1.count == output2.count
    assert output1.summary == output2.summary
    assert output1.sample_ids == output2.sample_ids


def test_series_headers_output_structure():
    """
    Test that the output structure is correct and contains all required fields.
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create input
    input_data = GetSeriesHeadersInput(parameter_id="Kwel")

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_headers(ctx, input_data))

    # Test output structure
    assert hasattr(output, "count")
    assert hasattr(output, "summary")
    assert hasattr(output, "sample_ids")
    assert hasattr(output, "available_filters")
    assert hasattr(output, "follow_up_suggestions")

    # Test data types
    assert isinstance(output.count, int)
    assert isinstance(output.summary, str)
    assert isinstance(output.sample_ids, str)
    assert isinstance(output.available_filters, dict)
    assert isinstance(output.follow_up_suggestions, list)

    # Test constraints
    assert output.count >= 0
    assert len(output.summary) <= 200
