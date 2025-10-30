"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from pydantic import BaseModel, Field
from talk_with_fews.models.base import LaxBaseModel


class GetConfigInfoInput(LaxBaseModel):
    """
    GetConfigInfoInput defines the input parameters for retrieving config information.
    """


class GetConfigInfoOutput(BaseModel):
    """Model for the output of the get_config_info tool.

    This model provides search results optimized for LLM consumption with
    structured data and actionable contextual description.
    """

    config_name: str = Field(..., description="Name of the config")
    description: str = Field(
        ...,
        description="Contextual description of the config to give the user more information",
    )
