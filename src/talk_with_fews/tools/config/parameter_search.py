from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps, ParameterBase
from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def search_parameters(
    ctx: RunContext[Deps], input: GetParameterInput
) -> GetParameterOutput:
    """Search for parameters matching the given criteria.

    This tool searches for parameters based on their names and optionally
    filters by module configuration. It supports limiting the number of results.

    Args:
        ctx: RunContext with database connection
        input: Search criteria including description pattern and optional filters

    Returns:
        GetParameterOutput containing matching transformations
    """

    if input.filter_parameters_name:
        query = """
        SELECT DISTINCT parid FROM ts_sets WHERE parid LIKE ? ORDER BY parid limit ?
        """
        params = [f"%{input.filter_parameters_name}%", input.number_of_parameters]
    else:
        query = """
        SELECT DISTINCT parid FROM ts_sets ORDER BY parid limit ?
        """
        params = [input.number_of_parameters]

    # Execute the query
    cursor = ctx.deps.db_connection.cursor()
    cursor.execute(query, params)
    results = []

    for row in cursor.fetchall():
        result = ParameterBase(id=row[0])
        results.append(result)

    # Generate description
    if len(results) > 0:
        description = f"Found {len(results)} parameter IDs matching the criteria. These parameter IDs can be used to search for timeseries using the search_timeseries tool."
    else:
        description = "No parameter IDs found matching the criteria."

    return GetParameterOutput(parameters=results, description=description)
