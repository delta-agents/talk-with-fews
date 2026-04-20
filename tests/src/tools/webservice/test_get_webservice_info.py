"""
Tests for the get_series_headers functionality.

This module tests the series headers retrieval with incremental caching,
including parameter-based and location-based queries.
"""

import asyncio
import os
from talk_with_fews.tools.webservice.get_webservice_info import get_webservice_info
from talk_with_fews.models.webservice.get_webservice_info import (
    GetWebServiceInfoInput,
    GetWebServiceInfoOutput,
)
from talk_with_fews.routers.setup_connections import get_runtime_ctx
from tests.utils_tests import setup_dot_env
from tests.test_config import get_test_service_config
from tests.parallel_decorator import fews_parallel


@fews_parallel(
    "actueelwaterbeeld",
)  #  "hdsr", "wsvv", "hhd", "scheldestromen")
def test_get_webservice_info(service):
    """
    Test the get_webservice_info function against all FEWS services.
    """
    # Set service explicitly
    os.environ["FEWS_TEST_SERVICE"] = service

    # Setup environment
    user_settings = setup_dot_env()
    service_config = get_test_service_config()
    test_data = service_config.test_data
    test_data["parameter_ids"]

    # Create input for parameter-based query
    input_data = GetWebServiceInfoInput()

    # Get runtime context
    ctx = get_runtime_ctx(user_settings)

    # Call the function
    output: GetWebServiceInfoOutput = asyncio.run(get_webservice_info(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output.webservice_name, str)
    assert isinstance(output.current_date, str)
    assert isinstance(output.description, str)
