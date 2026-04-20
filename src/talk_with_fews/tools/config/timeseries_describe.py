from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.config.sql_query import SQLQueryInput
from talk_with_fews.models.base import Deps, TimeSeriesProperties

from talk_with_fews.models.config.timeseries_describe import (
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.utils.schema_utils import format_timeseries_description


@log_tool_call
async def describe_timeseries(
    ctx: RunContext[Deps], input: DescribeTimeSeriesInput
) -> DescribeTimeSeriesOutput:
    """
    Get a complete description of a time series, including its basic properties and optionally
    any transformations that use it as input or output.

    The time series is described by the template:
    "{modins}|{vtype}|{parid}|{qualifiers}|{tstype}|{timess}"

    Args:
        ctx: RunContext with database connection
        input: DescribeTimeSeriesInput containing the time series ID to describe and whether to include transformations

    Returns:
        DescribeTimeSeriesOutput: A complete description of the time series including:
            - Structured data about the time series and optionally its transformations
            - Pre-formatted markdown content for display
    """
    # First get the basic time series information
    base_query = f"""
    SELECT id, modins, vtype, parid, qualifiers, tstype, timess
    FROM ts_sets
    WHERE id = {input.timeseries_id}
    """

    base_result = await execute_query(ctx, SQLQueryInput(query=base_query))

    if not base_result.results:
        raise ModelRetry(f"No time series found with ID {input.timeseries_id}")

    # Create the time series properties
    time_series = base_result.results[0]
    time_series["description"] = format_timeseries_description(time_series)

    # Get transformations if requested
    if input.include_transformations:
        transformations_query = f"""
        SELECT l.inout, t.idx as trafo_idx, t.description as trafo_description, t.ord_nr,
               cs.id as workflow_id, cs.wf_id as workflow_name, cs.description as workflow_desc,
               linked_ts.modins as linked_tss_modins, linked_ts.parid as linked_tss_parid, linked_ts.qualifiers as linked_tss_qualifiers,
               mc.modins as module_config,
               mc.id as module_config_id
        FROM links l
        JOIN trafos t ON l.trafo_idx = t.idx
        JOIN modins_calls mc ON t.mic_id = mc.id
        JOIN call_stacks cs ON mc.call_stack_id = cs.id
        JOIN links linked_l ON t.idx = linked_l.trafo_idx
            AND linked_l.tss_id != {input.timeseries_id}
        JOIN ts_sets linked_ts ON linked_l.tss_id = linked_ts.id
        WHERE l.tss_id = {input.timeseries_id}
        ORDER BY cs.wf_id, t.ord_nr
        """

        transformations_result = await execute_query(
            ctx, SQLQueryInput(query=transformations_query)
        )
        time_series["transformations"] = transformations_result.results

    # Create markdown content
    markdown_content = f"""## Time Series {time_series["id"]}
**Description:** {time_series["description"]}

### Properties
| Property | Value |
|----------|--------|
| Module Instance | {time_series["modins"]} |
| Value Type | {time_series["vtype"]} |
| Parameter ID | {time_series["parid"]} |
| Qualifiers | {time_series["qualifiers"]} |
| Time Series Type | {time_series["tstype"]} |
| Time Step | {time_series["timess"]} |

"""

    # Add transformations table if they exist and were requested
    if input.include_transformations and time_series.get("transformations"):
        markdown_content += """### Transformations
| Module Config | Transformation | Type | Workflow Name | Description |
|--------------|---------------|------|--------------|-------------|
"""
        for trans in time_series["transformations"]:
            markdown_content += f"| {trans['module_config']} | {trans['trafo_description']} | {trans['inout']} | {trans['workflow_name']} | {trans['workflow_desc']} |\n"
    elif input.include_transformations:
        markdown_content += "### Transformations\nNo transformations found"

    # Create the output using Pydantic models
    return DescribeTimeSeriesOutput(
        results=[TimeSeriesProperties(**time_series)], markdown_content=markdown_content
    )
