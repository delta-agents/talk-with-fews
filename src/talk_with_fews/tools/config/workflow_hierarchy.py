from pydantic_ai import RunContext, ModelRetry
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.models.config.workflow_hierarchy import WorkflowCallHierarchyInput
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import logger


@log_tool_call
async def find_workflow_call_hierarchy(
    ctx: RunContext[Deps], input: WorkflowCallHierarchyInput
) -> SQLQueryOutput:
    """
    Trace workflow call stacks.

    Args:
        ctx: RunContext with database connection
        input: WorkflowCallHierarchy model instance

    Returns:
        SQLQueryOutput: Workflow call hierarchy
    """
    root_workflow_id = input.root_workflow_id
    if not root_workflow_id:
        logger.warning("find_workflow_call_hierarchy called without root_workflow_id")
        raise ModelRetry("root_workflow_id is required")

    query = f"""
    WITH RECURSIVE workflow_hierarchy AS (
        SELECT id, wf_id, desc, parent_id, 0 AS level
        FROM call_stacks
        WHERE id = {root_workflow_id}

        UNION ALL

        SELECT cs.id, cs.wf_id, cs.desc, cs.parent_id, wh.level + 1
        FROM call_stacks cs
        JOIN workflow_hierarchy wh ON cs.parent_id = wh.id
    )
    SELECT id, wf_id, desc, parent_id, level
    FROM workflow_hierarchy
    ORDER BY level, wf_id
    """

    return await execute_query(ctx, SQLQueryInput(query=query))
