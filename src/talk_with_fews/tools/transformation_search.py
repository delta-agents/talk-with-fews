from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.models.transformation_search import (
    TransformationSearchInput,
    TransformationSearchOutput,
    TransformationSearchResult,
)
from talk_with_fews.utils.logging_utils import log_tool_call

    
@log_tool_call
async def search_transformations(
    ctx: RunContext[Deps], input_data: TransformationSearchInput
) -> TransformationSearchOutput:
    """Search for transformations matching the given criteria.

    This tool searches for transformations based on their description and optionally
    filters by workflow name and module configuration. It supports limiting the depth
    of hierarchical results.

    Args:
        ctx: RunContext with database connection
        input_data: Search criteria including description pattern and optional filters

    Returns:
        TransformationSearchOutput containing matching transformations
    """
    # Build the base query
    query = """
    SELECT DISTINCT
        t.id,
        t.desc,
        t.ord_nr,
        t.mic_id,
        mc.modins,
        cs.id as workflow_id,
        cs.wf_id as workflow_name,
        cs.desc as workflow_desc
    FROM trafos t
    JOIN modins_calls mc ON t.mic_id = mc.id
    JOIN call_stacks cs ON mc.call_stack_id = cs.id
    WHERE t.desc LIKE ?
    """
    params = [f"%{input_data.description_pattern}%"]

    # Add optional filters
    if input_data.workflow_name:
        query += " AND cs.wf_id LIKE ?"
        params.append(f"%{input_data.workflow_name}%")

    if input_data.module_config:
        query += " AND mc.modins LIKE ?"
        params.append(f"%{input_data.module_config}%")

    # Execute the query
    cursor = ctx.deps.db_connection.cursor()
    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        result = TransformationSearchResult(
            id=row[0],
            desc=row[1],
            ord_nr=row[2],
            mic_id=row[3],
            modins=row[4],
            workflow_id=row[5],
            workflow_name=row[6],
            workflow_desc=row[7],
        )
        results.append(result)

    # Generate markdown content
    markdown_content = "## Transformation Search Results\n\n"
    markdown_content += (
        f"Found {len(results)} transformations matching the criteria.\n\n"
    )

    if results:
        markdown_content += (
            "| Workflow | Module Config | Transformation | Order | Description |\n"
        )
        markdown_content += (
            "|----------|---------------|----------------|-------|-------------|\n"
        )

        for result in results:
            markdown_content += f"| {result.workflow_name} | {result.modins} | {result.id} | {result.ord_nr} | {result.desc} |\n"
    else:
        markdown_content += "No transformations found matching the criteria.\n"

    return TransformationSearchOutput(
        results=results, markdown_content=markdown_content
    )
