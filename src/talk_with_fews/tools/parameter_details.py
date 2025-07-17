import json
from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.parameter_details import (
    ParameterDetailsInput,
    ParameterDetailsOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.base import Parameter
import requests
from talk_with_fews.utils.webservice_utils import get_request


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
    show_attributes = input.show_attributes
    documentFormat = "PI_JSON"  # can also be PI_XML, but we default to JSON for now

    webservice_url = ctx.deps.webservice_url
    # check if webservice_url is set
    if webservice_url is None:
        raise ValueError(
            "Web service URL is not configured in the environment variables."
        )

    # Call the web service to get parameter details
    request_url = f"{webservice_url}/rest/fewspiservice/v1/parameters"
    params = dict(
        showAttributes={str(show_attributes).lower()}, documentFormat=documentFormat
    )
    error, data = get_request(request_url, params=params)
    data = json.loads(data) if isinstance(data, str) else data
    if error is not None:
        raise ValueError(f"Error fetching parameter details: {error}")

    parameters = []
    # Process the response data to create TimeSeriesSearchOutput
    for value in data["timeSeriesParameters"]:
        parameter = Parameter(
            id=value["id"],
            name=value["name"],
            parameter_type=value["parameterType"],
            unit=value["unit"],
            display_unit=value["displayUnit"],
            uses_datum=value["usesDatum"],
            parameter_group=value["parameterGroup"],
            parameter_group_name=value["parameterGroupName"],
            short_name=value["shortName"],
            attributes=value["attributes"] if show_attributes else None,
        )
        parameters.append(parameter)

        # Generate markdown content
    markdown_content = "## Parameters\n\n"
    markdown_content += f"Found {len(parameters)} parameters.\n\n"

    if parameters:
        markdown_content += "| ID | Name | Unit | parameterGroup |\n"
        markdown_content += "|----|------|------|----------------|\n"

        for parameter in parameters:
            markdown_content += f"| {parameter.id} | {parameter.name} | {parameter.unit} | {parameter.parameter_group} |\n"
    else:
        markdown_content += "No transformations found matching the criteria.\n"

    return ParameterDetailsOutput(
        parameters=parameters,
        markdown_content=markdown_content,
    )
