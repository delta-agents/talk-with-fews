from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.timeseries_search import search_timeseries
from talk_with_fews.models import (
    TimeSeriesSearchInput,
    TimeSeriesSearchOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_search_timeseries():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    timeseries_search_input = TimeSeriesSearchInput(module_instance="im.wiwb.knmi")

    timeseries_search_output: TimeSeriesSearchOutput = asyncio.run(
        search_timeseries(ctx=ctx, input=timeseries_search_input)
    )
    assert isinstance(timeseries_search_output, TimeSeriesSearchOutput)
    assert timeseries_search_output.results is not None
