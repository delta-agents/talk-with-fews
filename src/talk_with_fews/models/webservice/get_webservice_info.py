"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from pydantic import BaseModel, Field
from talk_with_fews.models.base import LaxBaseModel


class GetWebServiceInfoInput(LaxBaseModel):
    """
    GetWebServiceInfoInput defines the input parameters for retrieving web service information.
    """


class GetWebServiceInfoOutput(BaseModel):
    """Model for the output of the get_webservice_info tool.

    This model provides search results optimized for LLM consumption with
    structured data and actionable contextual description.
    """

    webservice_name: str = Field(..., description="Name of the web service")
    current_date: str = Field(
        ...,
        description="Current Date when the request was made by the user, use this to respond with relative questions like 'yesterday' and 'last month'",
    )
    description: str = Field(
        ...,
        description="Contextual description of the web service to give the user more information",
    )
