from pydantic_ai import RunContext

from talk_with_fews.models.config.sql_query import SQLQueryInput
from talk_with_fews.models.base import Deps

from talk_with_fews.models.config.workflow_search import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
    WorkflowSearchResult,
)
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def search_workflows(
    ctx: RunContext[Deps], input: WorkflowSearchInput
) -> WorkflowSearchOutput:
    """
    Search for workflows by name pattern.

    Args:
        ctx: RunContext with database connection
        input: WorkflowSearchInput containing the name pattern

    Returns:
        WorkflowSearchOutput: Matching workflows with formatted markdown content
    """
    query = f"""
    SELECT cs.id, cs.wf_id, cs.description,
           GROUP_CONCAT(mc.id) as module_config_ids
    FROM call_stacks cs
    LEFT JOIN modins_calls mc ON cs.id = mc.call_stack_id
    WHERE cs.wf_id LIKE '%{input.name_pattern}%' OR cs.description LIKE '%{input.name_pattern}%'
    GROUP BY cs.id
    ORDER BY cs.wf_id
    """

    result = await execute_query(ctx, SQLQueryInput(query=query))

    # Convert results to WorkflowSearchResult objects
    workflow_results = [
        WorkflowSearchResult(
            id=row["id"],
            wf_id=row["wf_id"],
            desc=row["description"],
            module_config_ids=row["module_config_ids"].split(",")
            if row["module_config_ids"]
            else [],
        )
        for row in result.results
    ]

    # Generate markdown content
    markdown_content = f"""## Workflow Search Results
Found {len(workflow_results)} workflows matching the pattern '{input.name_pattern}'.

| ID | Workflow ID | Description | Module Config IDs |
|----|-------------|-------------|-------------------|
"""

    for workflow in workflow_results:
        module_configs = (
            ", ".join(workflow.module_config_ids)
            if workflow.module_config_ids
            else "None"
        )
        markdown_content += f"| {workflow.id} | {workflow.wf_id} | {workflow.desc} | {module_configs} |\n"

    return WorkflowSearchOutput(
        results=workflow_results, markdown_content=markdown_content
    )
