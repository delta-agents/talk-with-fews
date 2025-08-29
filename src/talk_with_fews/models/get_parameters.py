"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Parameter, LaxBaseModel


class GetParameterInput(LaxBaseModel):
    """Model representing a parameter search result.

    Attributes:
        number_of_parameters (Optional[int]): The maximum number of parameters to retrieve.
        filter_parameters_name (Optional[str]): An optional name filter for parameters names, using the SQL LIKE functionality.

    A parameter search result extends the base time series properties with optional
    transformation information for search results.
    """

    number_of_parameters: Optional[int] = Field(
        ..., description="Number of parameter to retrieve"
    )
    filter_parameters_name: Optional[str] = Field(
        None,
        description="Optional string used to filter the parameters returned by using sql LIKE functionality",
    )


class GetParameterOutput(BaseModel):
    """Model for the output of the parameter_details
      tool.

    This model provides the search results including both structured data
    and a formatted markdown representation for display purposes.
    """

    parameters: Optional[List[Parameter]] = Field(
        None, description="Optional list of associated transformations"
    )

    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the search results in a human-readable format",
    )
