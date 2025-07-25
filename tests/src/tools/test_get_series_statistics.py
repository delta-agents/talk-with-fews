"""
Tests for the get_series_statistics functionality.

This module tests the series statistics retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio

from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_series_statistics
from tests.utils_tests import setup_dot_env


def test_get_series_statistics_no_date():
    """
    Test the get_series_statistics function without specifying a date range.
    """
    # Setup environment
    setup_dot_env()

    # Create input for parameter-based query
    input_data = GetSeriesStatisticsInput(parameter_id="Eref.d", location_id="KNMIUUR278")

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert output.count >= 600  # Should be non-negative


def test_get_series_statistics_empty():
    """
    Test the get_series_statistics function when the data is empty.
    """
    # Setup environment
    setup_dot_env()

    # Create input for parameter-based query
    input_data = GetSeriesStatisticsInput(parameter_id="Kwel", location_id="GPG_10")

    # Get runtime context
    ctx = get_runtime_ctx()

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert output.count == 0  # Should be non-negative

