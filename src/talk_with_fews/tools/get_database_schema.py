from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.schema_utils import (
    create_schema_info_dict,
    extract_db_schema_as_dict,
    get_table_relationships,
)
from talk_with_fews.models.database_schema import DatabaseSchemaOutput


@log_tool_call
async def get_database_schema(
    ctx: RunContext[Deps], input: dict = None
) -> DatabaseSchemaOutput:
    """
    Get the database schema information to understand the structure of the FEWS configuration database.

    Args:
        ctx: RunContext with database connection
        input: Optional dict with parameters (not used currently)

    Returns:
        Dict[str, Any]: Database schema information
    """
    try:
        # If we already have schema info, use it
        if hasattr(ctx.deps, "schema") and ctx.deps.schema:
            logger.info("Using cached schema information")
            schema = ctx.deps.schema

            # Return simplified view of schema for tool response
            return {
                "tables": create_schema_info_dict(schema),
                "relationships": get_table_relationships(schema),
                "sample_data": schema.get("sample_data", {}),
            }

        # Otherwise, extract the schema
        db_path = ctx.deps.db_path
        if not db_path:
            raise ModelRetry(
                "No database path provided. Cannot extract schema information."
            )

        # Extract schema using schema_utils
        logger.info(f"Extracting schema from database: {db_path}")
        schema = extract_db_schema_as_dict(db_path)

        # Cache schema for future use
        ctx.deps.schema = schema

        # Return formatted schema information
        return DatabaseSchemaOutput(
            tables=create_schema_info_dict(schema),
            relationships=get_table_relationships(schema),
            sample_data=schema.get("sample_data", {}),
        )

    except Exception as e:
        error_msg = f"Error retrieving database schema: {str(e)}"
        logger.error(error_msg)
        raise ModelRetry(error_msg)
