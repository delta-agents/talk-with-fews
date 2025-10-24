"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import ParameterBase, Parameter, LaxBaseModel


class GetParameterInput(LaxBaseModel):
    """Model representing a parameter search result.

    Attributes:
        number_of_parameters (Optional[int]): The maximum number of parameters to retrieve.
        filter_parameters_name (Optional[str]): An optional filter to search parameters by their id, name, or shortName, using the SQL LIKE functionality.

    A parameter search result extends the base time series properties with optional
    transformation information for search results.
    """

    number_of_parameters: Optional[int] = Field(
        ..., description="Number of parameter to retrieve"
    )
    filter_parameters_name: Optional[str] = Field(
        None,
        description="Optional string used to filter parameters by searching id, name, and shortName using SQL LIKE functionality",
    )


class GetParameterOutput(BaseModel):
    """Model for the output of the get_parameters tool.

    This model provides search results optimized for LLM consumption with
    structured data and actionable contextual description.

    Note: The 'display_unit' field in Parameter objects is the key field to use
    for AI communication and user-facing displays.
    """

    parameters: List[ParameterBase | Parameter] = Field(
        ...,
        description="List of matching parameters. Use the 'display_unit' field for AI communication.",
    )
    description: str = Field(
        ...,
        description="Contextual description with actionable insights for follow-up analysis",
    )
