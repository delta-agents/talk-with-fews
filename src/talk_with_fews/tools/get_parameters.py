import duckdb
from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.get_parameters import (
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
    # TODO adjust input to filter on parameters
    # Query parameters from DuckDB
    if input.number_of_parameters is not None:
        n = input.number_of_parameters  
    else:
        n = 10

    if input.query is not None:
        query = input.query
    else:
        query = """
        SELECT
            id,
            name,
            parameter_type,
            unit,
            display_unit,
            uses_datum,
            parameter_group,
            parameter_group_name,
            short_name,
            attributes
        FROM parameters
    """
    if "LIMIT" not in query:
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
        "parameter_group_name",
        "short_name",
        "attributes",
    ]
    # Convert rows to Parameter objects
    parameters = [Parameter(**dict(zip(col_names, row))) for row in rows]

    # make a summary of the locations

    # TODO change this to make a summary of the parameters
    # Generate markdown content

    markdown_content = "## Parameters\n\n"
    markdown_content += f"Found {len(parameters)} parameters.\n\n"

    if parameters:
        markdown_content += "| ID | Name | Unit | parameterGroup |\n"
        markdown_content += "|----|------|------|----------------|\n"

        for parameter in parameters:
            markdown_content += f"| {parameter.id} | {parameter.name} | {parameter.unit} | {parameter.parameter_group} |\n"
    else:
        markdown_content += "No parameters found matching the criteria.\n"

    return GetParameterOutput(
        parameters=parameters,
        markdown_content=markdown_content,
    )
