"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Parameter #, Location


class GetParameterInput(BaseModel):
    """Model representing a parameter search result.

    A parameter search result extends the base time series properties with optional
    transformation information for search results.
    """
    # locations: Optional[list[Location]] = Field(
    #     None,
    #     description="Optional list of Locations, these are used to filter parameters, obtainable from the tool get_locations",
    # )
    show_attributes: bool = Field(
        False, description="Show parameter attributes, defaults to False"
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
