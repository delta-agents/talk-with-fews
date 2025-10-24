from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.config.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.models.config.sql_query import SQLQueryInput

from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.models.base import Deps


@log_tool_call
async def analyze_dependencies(
    ctx: RunContext[Deps], input: DependencyAnalysisInput
) -> DependencyAnalysisOutput:
    """
    Analyze dependencies for a specific entity, showing both upstream and downstream relationships.

    Args:
        ctx: RunContext with database connection
        input: DependencyAnalysisInput containing entity details and analysis direction

    Returns:
        DependencyAnalysisOutput: A complete description of dependencies including:
            - Structured data about the dependencies
            - Pre-formatted markdown content for display
    """
    if input.entity_type == "timeseries":
        # For time series, show both producers and consumers
        query = f"""
        WITH producers AS (
            -- Find transformations that produce this time series
            SELECT
                t.id as trafo_id, t.desc as trafo_desc, t.ord_nr,
                mc.id as module_config_id, mc.modins as module_config,
                cs.id as workflow_id, cs.wf_id as workflow_name, cs.desc as workflow_desc,
                'out' as link_type
            FROM trafos t
            JOIN links l ON t.id = l.trafo_id
            JOIN modins_calls mc ON t.mic_id = mc.id
            JOIN call_stacks cs ON mc.call_stack_id = cs.id
            WHERE l.tss_id = {input.entity_id} AND l.inout = 'out'
        ),
        consumers AS (
            -- Find transformations that consume this time series
            SELECT
                t.id as trafo_id, t.desc as trafo_desc, t.ord_nr,
                mc.id as module_config_id, mc.modins as module_config,
                cs.id as workflow_id, cs.wf_id as workflow_name, cs.desc as workflow_desc,
                'in' as link_type
            FROM trafos t
            JOIN links l ON t.id = l.trafo_id
            JOIN modins_calls mc ON t.mic_id = mc.id
            JOIN call_stacks cs ON mc.call_stack_id = cs.id
            WHERE l.tss_id = {input.entity_id} AND l.inout = 'in'
        )
        SELECT * FROM producers
        UNION ALL
        SELECT * FROM consumers
        ORDER BY link_type, workflow_name, ord_nr
        """
    elif input.entity_type == "transformation":
        # For transformations, show both inputs and outputs
        query = f"""
        WITH inputs AS (
            -- Find input time series
            SELECT
                ts.id as tss_id,
                'in' as link_type
            FROM ts_sets ts
            JOIN links l ON ts.id = l.tss_id
            WHERE l.trafo_id = {input.entity_id} AND l.inout = 'in'
        ),
        outputs AS (
            -- Find output time series
            SELECT
                ts.id as tss_id,
                'out' as link_type
            FROM ts_sets ts
            JOIN links l ON ts.id = l.tss_id
            WHERE l.trafo_id = {input.entity_id} AND l.inout = 'out'
        )
        SELECT * FROM inputs
        UNION ALL
        SELECT * FROM outputs
        ORDER BY link_type, tss_id
        """
    elif input.entity_type == "workflow":
        # For workflows, show both callers and callees
        query = f"""
        WITH callers AS (
            -- Find workflows that call this workflow
            SELECT
                parent.id, parent.wf_id, parent.desc,
                'in' as link_type
            FROM call_stacks parent
            JOIN call_stacks child ON child.parent_id = parent.id
            WHERE child.id = {input.entity_id}
        ),
        callees AS (
            -- Find workflows called by this workflow
            SELECT
                child.id, child.wf_id, child.desc,
                'out' as link_type
            FROM call_stacks child
            WHERE child.parent_id = {input.entity_id}
        )
        SELECT * FROM callers
        UNION ALL
        SELECT * FROM callees
        ORDER BY link_type, wf_id
        """
    else:
        logger.warning(
            f"analyze_dependencies called with unknown entity type: {input.entity_type}"
        )
        raise ModelRetry(f"Unknown entity type: {input.entity_type}")

    result = await execute_query(ctx, SQLQueryInput(query=query))

    if not result.results:
        return DependencyAnalysisOutput(
            results=[],
            markdown_content=f"No dependencies found for {input.entity_type} with ID {input.entity_id}",
        )

    # Create markdown content based on entity type
    if input.entity_type == "timeseries":
        markdown_content = f"""## Dependencies for Time Series {input.entity_id}

### Producers
| Module Config | Transformation | Order | Workflow | Description |
|--------------|---------------|-------|----------|-------------|
"""
        for row in result.results:
            if row["link_type"] == "out":
                markdown_content += f"| {row['module_config']} | {row['trafo_desc']} | {row['ord_nr']} | {row['workflow_name']} | {row['workflow_desc']} |\n"

        markdown_content += "\n### Consumers\n| Module Config | Transformation | Order | Workflow | Description |\n|--------------|---------------|-------|----------|-------------|\n"
        for row in result.results:
            if row["link_type"] == "in":
                markdown_content += f"| {row['module_config']} | {row['trafo_desc']} | {row['ord_nr']} | {row['workflow_name']} | {row['workflow_desc']} |\n"

    elif input.entity_type == "transformation":
        markdown_content = f"""## Dependencies for Transformation {input.entity_id}

### Input Time Series
| Time Series ID |
|----------------|
"""
        for row in result.results:
            if row["link_type"] == "in":
                markdown_content += f"| {row['tss_id']} |\n"

        markdown_content += (
            "\n### Output Time Series\n| Time Series ID |\n|----------------|\n"
        )
        for row in result.results:
            if row["link_type"] == "out":
                markdown_content += f"| {row['tss_id']} |\n"

    else:  # workflow
        markdown_content = f"""## Dependencies for Workflow {input.entity_id}

### Callers
| Workflow ID | Name | Description |
|------------|------|-------------|
"""
        for row in result.results:
            if row["link_type"] == "in":
                markdown_content += (
                    f"| {row['id']} | {row['wf_id']} | {row['desc']} |\n"
                )

        markdown_content += "\n### Callees\n| Workflow ID | Name | Description |\n|------------|------|-------------|\n"
        for row in result.results:
            if row["link_type"] == "out":
                markdown_content += (
                    f"| {row['id']} | {row['wf_id']} | {row['desc']} |\n"
                )

    return DependencyAnalysisOutput(
        results=result.results, markdown_content=markdown_content
    )
