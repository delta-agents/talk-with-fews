from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.get_database_schema import get_database_schema
from talk_with_fews.models import (
    DatabaseSchemaInput,
    DatabaseSchemaOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_database_schema():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    database_schema_input = DatabaseSchemaInput()

    database_schema_output: DatabaseSchemaOutput = asyncio.run(
        get_database_schema(ctx=ctx, input=database_schema_input)
    )
    assert isinstance(
        DatabaseSchemaOutput(**database_schema_output), DatabaseSchemaOutput
    )
