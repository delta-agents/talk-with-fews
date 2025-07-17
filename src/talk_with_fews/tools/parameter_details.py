from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.parameter_details import (
    ParameterDetailsInput,
    ParameterDetailsOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def get_parameter_details(
    ctx: RunContext[Deps], input: ParameterDetailsInput
) -> ParameterDetailsOutput:
    """
    Search for time series sets by parameter, qualifier, module, or endpoint status.

    Args:
        ctx: RunContext with database connection
        input: TimeSeriesSearchInput containing search criteria

    Returns:
        TimeSeriesSearchOutput: Matching time series sets with formatted markdown content
    """
    show_attributes = input.get("show_attributes", False) 
    documentFormat = input.get("documentFormat", "PI_JSON")

    webservice_url = ctx.deps.webservice_url
    # check if webservice_url is set
    if webservice_url is None:
        raise ValueError("Web service URL is not configured in the environment variables.")
    
    ctx, show_attributes, documentFormat
    return ParameterDetailsOutput(
        # results=time_series_results, markdown_content=markdown_content
    )
