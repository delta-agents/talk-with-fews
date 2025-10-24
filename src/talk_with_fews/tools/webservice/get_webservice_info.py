from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.webservice.get_webservice_info import (
    GetWebServiceInfoInput,
    GetWebServiceInfoOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from datetime import datetime


@log_tool_call
async def get_webservice_info(
    ctx: RunContext[Deps], input: GetWebServiceInfoInput
) -> GetWebServiceInfoOutput:
    """
    Retrieve a given number of location details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: GetWebServiceInfoInput
    Returns:
        GetWebServiceInfoOutput: Retrieved web service information
    """
    webservice_name = ctx.deps.webservice_name
    current_time = datetime.now().isoformat()
    description = (
        "FEWS is a Forecast Early Warning System used to store and manage hydrological data."
        f"The web service '{webservice_name}' provides access to these hydrological data and services. "
        f"This set of mcp tools allows the user to interact with the web service for data retrieval and analysis."
    )

    return GetWebServiceInfoOutput(
        webservice_name=webservice_name,
        current_time=current_time,
        description=description,
    )
