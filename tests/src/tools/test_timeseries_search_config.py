from talk_with_fews.models import (
    TimeSeriesSearchInput,
    TimeSeriesSearchOutput,
)
from talk_with_fews.tools import search_timeseries
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_locations():
    """
    Test the get_locations function to ensure it retrieves locations details correctly.
    """
    # this is dependant on the FEWS web service being available indefinitely
    user_settings = setup_dot_env()
    # Create a mock RunContext and input
    timeseries_search_input = TimeSeriesSearchInput(module_instance="im.wiwb.knmi")
    # Call the function
    ctx = get_runtime_ctx(user_settings)
    output: TimeSeriesSearchOutput = asyncio.run(
        search_timeseries(ctx, timeseries_search_input)
    )

    # Assert the output is of the expected type
    assert isinstance(output, TimeSeriesSearchOutput)
    assert output.results is not None
    assert len(output.results) > 1  # Expecting many results
    assert output.results[0].id == 142
