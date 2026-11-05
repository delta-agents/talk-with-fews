from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.models import (
    SQLQueryInput,
    SQLQueryOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_execute_query():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    sql_query_input = SQLQueryInput(
        query="SELECT * FROM trafos",
    )

    sql_query_output: SQLQueryOutput = asyncio.run(
        execute_query(ctx=ctx, input=sql_query_input)
    )
    assert isinstance(sql_query_output, SQLQueryOutput)
