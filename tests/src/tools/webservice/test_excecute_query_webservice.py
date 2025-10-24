from talk_with_fews.models.config.sql_query import (
    SQLQueryInput,
    SQLQueryOutput,
)
from talk_with_fews.tools import execute_query_webservice
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
    input_data = SQLQueryInput(
        query="SELECT * FROM locations WHERE shortName = 'Esvelder beek' LIMIT 1"
    )

    # Call the function
    ctx = get_runtime_ctx(user_settings)
    output = asyncio.run(execute_query_webservice(ctx, input_data))

    # Assert the output is of the expected type
    assert isinstance(output, SQLQueryOutput)
    assert output.results is not None
    assert len(output.results) == 1  # Expecting one result for the specific location
    assert output.results[0]["shortName"] == "Esvelder beek"
