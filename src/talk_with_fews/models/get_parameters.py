"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import format_as_xml
from talk_with_fews.models.base import Parameter  # , Location


class TalkWithFewsBase(BaseModel):
    def to_xml(self) -> str:
        """Convert the output to an XML string."""
        return format_as_xml(self, root_tag="GetParameterOutput")

    def __repr__(self):
        return self.to_xml()

    def json(self):
        return self.to_xml()


class GetParameterInput(BaseModel):
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


class GetParameterOutput(TalkWithFewsBase):
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
