import duckdb
from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.base import Parameter


@log_tool_call
async def get_parameters(
    ctx: RunContext[Deps], input: GetParameterInput
) -> GetParameterOutput:
    """
    Retrieve parameter details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: ParameterDetailsInput containing request parameters
    Returns:
        ParameterDetailsOutput: Retrieved parameter details with formatted markdown content
    """
    # Query parameters from DuckDB
    if input.number_of_parameters is not None:
        n = input.number_of_parameters
    else:
        n = 10

    columns = "id,name,parameter_type,unit,display_unit,uses_datum,parameter_group,short_name,attributes"

    # Build WHERE clause - enhanced search across multiple columns
    if input.filter_parameters_name is not None:
        # Search across id, name, and short_name columns (enhanced search like get_locations)
        query = f"SELECT {columns} FROM parameters WHERE id ILIKE '%{input.filter_parameters_name}%' OR name ILIKE '%{input.filter_parameters_name}%' OR short_name ILIKE '%{input.filter_parameters_name}%'"
    else:
        query = f"SELECT {columns} FROM parameters"

    query += f" LIMIT {n}"

    connection: duckdb.DuckDBPyConnection = ctx.deps.cache_FewsWebServices_db
    cursor = connection.cursor()
    data = cursor.execute(query)
    rows = data.fetchall()

    # Convert rows to Parameter objects
    col_names = [
        "id",
        "name",
        "parameter_type",
        "unit",
        "display_unit",
        "uses_datum",
        "parameter_group",
        "short_name",
        "attributes",
    ]
    # Convert rows to Parameter objects
    parameters = [Parameter(**dict(zip(col_names, row))) for row in rows]

    # Generate brief, clear summary following get_locations pattern
    if not parameters:
        if input.filter_parameters_name:
            description = (
                f"No parameters found matching '{input.filter_parameters_name}'"
            )
        else:
            description = "No parameters available"
    else:
        count = len(parameters)

        # Analyze the results to provide clear summary based on actual data structure
        parameter_groups = {}
        for param in parameters:
            group = param.parameter_group or "Unknown"
            parameter_groups[group] = parameter_groups.get(group, 0) + 1

        if count == 1:
            param = parameters[0]
            short_name = param.short_name if param.short_name else param.name
            # Only show display_unit if it's different from what's already in short_name
            display_unit = (
                f" ({param.display_unit})"
                if param.display_unit and param.display_unit not in short_name
                else ""
            )
            description = f"Found 1 parameter: '{short_name}{display_unit}'"
        elif count <= 5:
            # For small results, mention key details
            if len(parameter_groups) == 1:
                group_name = list(parameter_groups.keys())[0]
                description = f"Found {count} parameters in group '{group_name}'"
            else:
                parameter_summaries = []
                for p in parameters[:3]:
                    short_name = p.short_name if p.short_name else p.name
                    # Only show display_unit if it's different from what's already in short_name
                    display_unit = (
                        f" ({p.display_unit})"
                        if p.display_unit and p.display_unit not in short_name
                        else ""
                    )
                    parameter_summaries.append(f"'{short_name}{display_unit}'")
                if count > 3:
                    parameter_summaries.append(f"and {count - 3} more")
                description = (
                    f"Found {count} parameters: {', '.join(parameter_summaries)}"
                )
        else:
            # For larger results, provide summary
            if len(parameter_groups) == 1:
                group_name = list(parameter_groups.keys())[0]
                description = f"Found {count} parameters in group '{group_name}'"
            elif len(parameter_groups) <= 3:
                group_summary = ", ".join(
                    [
                        f"{count} in '{group}'"
                        for group, count in parameter_groups.items()
                    ]
                )
                description = f"Found {count} parameters: {group_summary}"
            else:
                description = (
                    f"Found {count} parameters across {len(parameter_groups)} groups"
                )

    return GetParameterOutput(
        parameters=parameters,
        description=description,
    )
