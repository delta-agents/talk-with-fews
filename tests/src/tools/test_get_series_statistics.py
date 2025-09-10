"""
Tests for the get_series_statistics functionality.

This module tests the series statistics retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
from datetime import datetime
from pydantic import ValidationError
import pytest

from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools import get_series_statistics
from tests.utils_tests import setup_dot_env


def test_get_series_statistics():
    """
    Test the get_series_statistics function
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create input for parameter-based query
    input_data = GetSeriesStatisticsInput(
        parameter_id="Eref.d",
        location_id="KNMIUUR278",
        start_time=datetime.fromisoformat("1990-01-01T00:00:00+00:00"),
        end_time=datetime.fromisoformat("2025-12-31T23:59:59+00:00"),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert output.count >= 0  # Should be non-negative


def test_get_series_statistics_data_empty():
    """
    Test the get_series_statistics function when the data is empty.
    """
    # Setup environment
    user_settings = setup_dot_env()

    # Create input for parameter-based query
    input_data = GetSeriesStatisticsInput(
        parameter_id="Kwel",
        location_id="GPG_10",
        start_time=datetime.fromisoformat("1990-01-01T00:00:00+00:00"),
        end_time=datetime.fromisoformat("2025-12-31T23:59:59+00:00"),
    )

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output = asyncio.run(get_series_statistics(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, GetSeriesStatisticsOutput)
    assert output.count == 0  # Should be non-negative


def test_get_series_statistics_no_input():
    """
    Test the get_series_statistics function when no input is provided.
    """
    # Call the function and expect ValidationError
    with pytest.raises(ValidationError):
        GetSeriesStatisticsInput()


# todo one input
def test_get_series_statistics_one_input():
    with pytest.raises(ValidationError):
        GetSeriesStatisticsInput(parameter_id="Kwel")
