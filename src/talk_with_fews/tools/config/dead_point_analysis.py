from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.dead_point_analysis import (
    DeadPoint,
    DeadPointProducer,
    DeadPointsAnalysisOutput,
    DeadPointsAnalysisInput,
)
from talk_with_fews.models.sql_query import SQLQueryInput

from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.models.base import Deps, ModuleSummary
from talk_with_fews.utils.schema_utils import format_timeseries_description


@log_tool_call
async def analyze_dead_points(
    ctx: RunContext[Deps], input: DeadPointsAnalysisInput = None
) -> DeadPointsAnalysisOutput:
    """
    Identify "dead points" in the FEWS configuration - time series sets that are
    neither used as inputs for any transformation nor marked as endpoints.

    Args:
        ctx: RunContext with database connection
        input: Optional dict with parameters (include_producers=True/False)

    Returns:
        DeadPointsAnalysisOutput: Analysis of dead points with formatted markdown content
    """
    try:
        # Check parameters
        include_producers = (
            input.include_producers
        )  # .get("include_producers", True) if input else True

        # Execute query to find dead points with their origins
        dead_points_query = """
        WITH dead_points AS (
            SELECT ts.id, ts.modins, ts.vtype, ts.parid, ts.qualifiers, ts.tstype, ts.timess
            FROM ts_sets ts
            WHERE ts.id NOT IN (
                -- TSS used as inputs for transformations
                SELECT DISTINCT tss_id
                FROM links
                WHERE inout = 'in'
            )
            AND ts.id NOT IN (
                -- TSS marked as endpoints
                SELECT tss_id
                FROM endpoints
            )
        )
        SELECT dp.*,
               t.id as trafo_id, t.desc as trafo_desc,
               mc.id as module_config_id, mc.modins as module_config,
               cs.id as workflow_id, cs.wf_id as workflow_name
        FROM dead_points dp
        LEFT JOIN links l ON dp.id = l.tss_id AND l.inout = 'out'
        LEFT JOIN trafos t ON l.trafo_id = t.id
        LEFT JOIN modins_calls mc ON t.mic_id = mc.id
        LEFT JOIN call_stacks cs ON mc.call_stack_id = cs.id
        ORDER BY dp.modins, dp.parid
        """

        dead_points_result = await execute_query(
            ctx, SQLQueryInput(query=dead_points_query)
        )

        # If no dead points found, return early
        if not dead_points_result.results:
            return DeadPointsAnalysisOutput(
                count=0,
                dead_points=[],
                module_summary=[],
                unique_modules=0,
                parameters_affected=0,
                recommendations=[
                    "No dead points found in the configuration.",
                    "All time series are either used as inputs or marked as endpoints.",
                ],
            )

        # Convert results to DeadPoint objects
        dead_points = []
        for row in dead_points_result.results:
            dead_point = DeadPoint(
                id=row["id"],
                modins=row["modins"],
                vtype=row["vtype"],
                parid=row["parid"],
                qualifiers=row["qualifiers"],
                tstype=row["tstype"],
                timess=row["timess"],
            )
            dead_points.append(dead_point)

        # Analyze by module instance
        module_counts = {}
        for dp in dead_points:
            if dp.modins in module_counts:
                module_counts[dp.modins] += 1
            else:
                module_counts[dp.modins] = 1

        # Convert to ModuleSummary objects
        module_summary = [
            ModuleSummary(module=module, count=count)
            for module, count in sorted(
                module_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

        # Get list of dead point IDs
        dead_point_ids = [dp.id for dp in dead_points]

        # Find transformations that produce these dead points
        producers = {}
        if include_producers and dead_point_ids:
            id_list = ", ".join(str(id) for id in dead_point_ids)

            producers_query = f"""
            SELECT l.tss_id, t.id AS trafo_id, t.desc AS trafo_desc,
                  m.modins AS module_instance, m.id as module_config_id,
                  c.wf_id AS workflow_id
            FROM links l
            JOIN trafos t ON l.trafo_id = t.id
            JOIN modins_calls m ON t.mic_id = m.id
            JOIN call_stacks c ON m.call_stack_id = c.id
            WHERE l.tss_id IN ({id_list})
            AND l.inout = 'out'
            ORDER BY l.tss_id
            """

            producers_result = await execute_query(
                ctx, SQLQueryInput(query=producers_query)
            )

            if producers_result.results:
                for row in producers_result.results:
                    tss_id = row["tss_id"]
                    if tss_id not in producers:
                        producers[tss_id] = []
                    producers[tss_id].append(
                        DeadPointProducer(
                            tss_id=row["tss_id"],
                            trafo_id=row["trafo_id"],
                            trafo_desc=row["trafo_desc"],
                            module_instance=row["module_instance"],
                            workflow_id=row["workflow_id"],
                        )
                    )

        # Analyze which module instances, parameters, and qualifiers can be removed
        dead_module_instances = set(dp.modins for dp in dead_points)
        dead_parameters = set(dp.parid for dp in dead_points)
        dead_qualifiers = set(dp.qualifiers for dp in dead_points)

        #### unused ?

        # Query ALL time series sets to determine which ones are exclusively used by dead points
        # all_timeseries_query = """
        # SELECT DISTINCT modins, parid, qualifiers
        # FROM ts_sets
        # """

        # all_timeseries_result = await execute_query(
        #     ctx, SQLQueryInput(query=all_timeseries_query)
        # )

        # Extract all module instances, parameters, and qualifiers from active time series
        # all_module_instances = set(
        #     row["modins"] for row in all_timeseries_result.results
        # )
        # all_parameters = set(row["parid"] for row in all_timeseries_result.results)
        # all_qualifiers = set(row["qualifiers"] for row in all_timeseries_result.results)

        # Filter out the module instances, parameters, and qualifiers that are also used by active time series
        active_timeseries_query = """
        SELECT DISTINCT ts.modins, ts.parid, ts.qualifiers
        FROM ts_sets ts
        WHERE ts.id IN (
            -- TSS used as inputs for transformations
            SELECT DISTINCT tss_id
            FROM links
            WHERE inout = 'in'
        )
        OR ts.id IN (
            -- TSS marked as endpoints
            SELECT tss_id
            FROM endpoints
        )
        """

        active_timeseries_result = await execute_query(
            ctx, SQLQueryInput(query=active_timeseries_query)
        )

        active_module_instances = set(
            row["modins"] for row in active_timeseries_result.results
        )
        active_parameters = set(
            row["parid"] for row in active_timeseries_result.results
        )
        active_qualifiers = set(
            row["qualifiers"] for row in active_timeseries_result.results
        )

        # Now identify the ones that are exclusively in dead points
        exclusively_dead_module_instances = (
            dead_module_instances - active_module_instances
        )
        exclusively_dead_parameters = dead_parameters - active_parameters
        exclusively_dead_qualifiers = dead_qualifiers - active_qualifiers

        # Filter module_summary to only include exclusively dead modules
        exclusively_module_summary = [
            ms
            for ms in module_summary
            if ms.module in exclusively_dead_module_instances
        ]

        # Create markdown content
        markdown_content = f"""## Dead Points Analysis
Found {len(dead_points)} dead points across {len(module_counts)} modules.

### Dead Points and Their Origins
| ID | Time Series | Transformation | Module Config | Workflow |
|----|-------------|----------------|---------------|----------|
"""

        for dp in dead_points:
            producers_info = producers.get(dp.id, [])
            if producers_info:
                for prod in producers_info:
                    ts_desc = format_timeseries_description(dp.model_dump())
                    markdown_content += f"| {dp.id} | {ts_desc} | {prod.trafo_desc} | {prod.module_instance} | {prod.workflow_id} |\n"
            else:
                ts_desc = format_timeseries_description(dp.model_dump())
                markdown_content += f"| {dp.id} | {ts_desc} | - | - | - |\n"

        if exclusively_dead_module_instances:
            markdown_content += "\n### Module Instances That Can Be Removed\n"
            markdown_content += "| Module Instance | Dead Points Count |\n"
            markdown_content += "|----------------|-------------------|\n"
            for ms in exclusively_module_summary:
                markdown_content += f"| {ms.module} | {ms.count} |\n"
        else:
            markdown_content += "\n### Module Instances That Can Be Removed\n"
            markdown_content += "No module instances can be safely removed - all are used by active time series.\n"

        if exclusively_dead_parameters:
            markdown_content += "\n### Parameters That Can Be Removed\n"
            markdown_content += "| Parameter |\n"
            markdown_content += "|-----------|\n"
            for param in sorted(exclusively_dead_parameters):
                markdown_content += f"| {param} |\n"
        else:
            markdown_content += "\n### Parameters That Can Be Removed\n"
            markdown_content += "No parameters can be safely removed - all are used by active time series.\n"

        if exclusively_dead_qualifiers:
            markdown_content += "\n### Qualifiers That Can Be Removed\n"
            markdown_content += "| Qualifier |\n"
            markdown_content += "|-----------|\n"
            for qual in sorted(exclusively_dead_qualifiers):
                markdown_content += f"| {qual} |\n"
        else:
            markdown_content += "\n### Qualifiers That Can Be Removed\n"
            markdown_content += "No qualifiers can be safely removed - all are used by active time series.\n"

        # Update recommendations
        recommendations = [
            "Review the identified dead points to determine if they are needed",
            "Consider removing unused time series sets to simplify configuration",
            "Check if any dead points should be marked as endpoints",
            "Verify if transformations producing these time series are working as expected",
        ]

        if exclusively_dead_module_instances:
            recommendations.append(
                f"Consider removing {len(exclusively_dead_module_instances)} unused module instances that are EXCLUSIVELY used by dead points"
            )

        if exclusively_dead_parameters:
            recommendations.append(
                f"Consider removing {len(exclusively_dead_parameters)} unused parameters that are EXCLUSIVELY used by dead points"
            )

        if exclusively_dead_qualifiers:
            recommendations.append(
                f"Consider removing {len(exclusively_dead_qualifiers)} unused qualifiers that are EXCLUSIVELY used by dead points"
            )

        # Add recommendations
        markdown_content += "\n### Recommendations\n"
        for rec in recommendations:
            markdown_content += f"- {rec}\n"

        return DeadPointsAnalysisOutput(
            count=len(dead_points),
            dead_points=dead_points,
            module_summary=exclusively_module_summary,  # Only include exclusively dead modules
            unique_modules=len(
                exclusively_dead_module_instances
            ),  # Only count exclusively dead modules
            parameters_affected=len(
                exclusively_dead_parameters
            ),  # Only count exclusively dead parameters
            producers=producers,
            recommendations=recommendations,
            markdown_content=markdown_content,
        )

    except Exception as e:
        error_msg = f"Error analyzing dead points: {str(e)}"
        logger.error(error_msg)
        raise ModelRetry(error_msg)
