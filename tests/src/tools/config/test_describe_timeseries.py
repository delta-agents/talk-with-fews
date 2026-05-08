from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.transformation_details import (
    get_transformation_details,
)
from talk_with_fews.tools.config.timeseries_describe import describe_timeseries
from talk_with_fews.models import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_describe_timeseries():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)

    # First get a transformation to extract a timeseries_id
    transformation_details_input = TransformationDetailsInput(
        transformation_id=1357,
    )
    transformation_details_output: TransformationDetailsOutput = asyncio.run(
        get_transformation_details(ctx=ctx, input=transformation_details_input)
    )
    timeseries_id = transformation_details_output.results[0].time_series_links[0].tss_id

    timeseries_describe_input = DescribeTimeSeriesInput(timeseries_id=timeseries_id)
    timeseries_describe_output: DescribeTimeSeriesOutput = asyncio.run(
        describe_timeseries(ctx=ctx, input=timeseries_describe_input)
    )
    assert isinstance(timeseries_describe_output, DescribeTimeSeriesOutput)
