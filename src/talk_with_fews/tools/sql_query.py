import sqlite3
import duckdb
from pydantic_ai import RunContext, ModelRetry

from talk_with_fews.models.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.models.base import Deps

from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.utils.schema_utils import (
    create_schema_info_dict,
    diagnose_sql_error,
)


@log_tool_call
async def execute_query(ctx: RunContext[Deps], input: SQLQueryInput) -> SQLQueryOutput:
    """
    Execute a SQL query on the FEWS configuration database.

    Args:
        ctx: RunContext with database connection
        input: SQLQueryInput containing the query to execute

    Returns:
        SQLQueryOutput: Results of the query with column names
    """
    try:
        # Execute the query
        cursor = ctx.deps.db_connection.cursor()
        cursor.execute(input.query)

        # Extract results and column names
        column_names = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )
        results = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        # Return the query results
        return SQLQueryOutput(
            results=results,
            column_names=column_names,
            row_count=len(results),
            query_executed=input.query,
        )
    except sqlite3.Error as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"SQL Error: {error_msg} - Query: {input.query}")

        # Attempt to diagnose common errors using schema_utils.diagnose_sql_error
        if hasattr(ctx.deps, "schema") and ctx.deps.schema:
            schema_info = create_schema_info_dict(ctx.deps.schema)
            error_diagnosis = diagnose_sql_error(str(e), input.query, schema_info)
            if error_diagnosis:
                error_msg += f" - {error_diagnosis}"

        raise ModelRetry(error_msg)


@log_tool_call
async def execute_query_webservice_cache(
    ctx: RunContext[Deps], input: SQLQueryInput
) -> SQLQueryOutput:
    """
    Execute a SQL query on the FewsWebService cached database.

    Args:
        ctx: RunContext with database connection
        input: SQLQueryInput containing the query to execute

    Returns:
        SQLQueryOutput: Results of the query with column names
    """
    try:
        # Execute the query
        connection : duckdb.DuckDBPyConnection = ctx.deps.cache_FewsWebServices_db
        cursor = connection.cursor()
        cursor.execute(input.query)

        # Extract results and column names
        column_names = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )
        results = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        # Return the query results
        return SQLQueryOutput(
            results=results,
            column_names=column_names,
            row_count=len(results),
            query_executed=input.query,
        )
    except duckdb.Error as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"SQL Error: {error_msg} - Query: {input.query}")

        # Attempt to diagnose common errors using schema_utils.diagnose_sql_error
        if hasattr(ctx.deps, "schema") and ctx.deps.schema:
            schema_info = create_schema_info_dict(ctx.deps.schema)
            error_diagnosis = diagnose_sql_error(str(e), input.query, schema_info)
            if error_diagnosis:
                error_msg += f" - {error_diagnosis}"

        raise ModelRetry(error_msg)
