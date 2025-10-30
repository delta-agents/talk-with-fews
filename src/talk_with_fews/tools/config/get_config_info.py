from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.config.get_config_info import (
    GetConfigInfoInput,
    GetConfigInfoOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def get_config_info(
    ctx: RunContext[Deps], input: GetConfigInfoInput
) -> GetConfigInfoOutput:
    """
    Retrieve a given number of location details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: GetConfigInfoInput
    Returns:
        GetConfigInfoOutput: Retrieved web service information
    """
    config_name = ctx.deps.config_name
    # For now
    description = (
        "FEWS is a Forecast Early Warning System used to store and manage hydrological data."
        f"The configuration '{config_name}' provides information on the workflows which occur in shaping the data processing. "
        f"This set of mcp tools allows the user to interact with the configuration, giving insights into data transformations and workflow structures."
    )

    return GetConfigInfoOutput(
        config_name=config_name,
        description=description,
    )
