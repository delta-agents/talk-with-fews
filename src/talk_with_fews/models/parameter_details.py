"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Parameter


class ParameterDetailsInput(BaseModel):
    """Model representing a parameter search result.

    A parameter search result extends the base time series properties with optional
    transformation information for search results.
    """

    show_attributes: bool = Field(
        False, description="Show parameter attributes, defaults to False"
    )


class ParameterDetailsOutput(BaseModel):
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
