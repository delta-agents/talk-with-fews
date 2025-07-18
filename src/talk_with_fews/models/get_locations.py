"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Location, Parameter


class GetLocationInput(BaseModel):
    """Model representing a location search result.

    A location search result extends the base time series properties with optional
    transformation information for search results.
    """

    parameters: Optional[list[Parameter]] = Field(
        None,
        description="Optional list of parameters, these are used to filter locations, obtainable from the tool get_parameters",
    )

    parameter_group: Optional[list[Parameter]] = Field(
        None,
        description="Optional list of parameter, whose Groupids to filter locations by",
    )

    show_attributes: bool = Field(
        False, description="Show location attributes, defaults to False"
    )

    show_parent_locations: bool = Field(
        False, description="Show parent locations, defaults to False"
    )

    show_thresholds: bool = Field(
        False, description="Show thresholds, defaults to False"
    )

    include_icon_names: bool = Field(
        False, description="Include icon names, defaults to False"
    )

    include_location_relations: bool = Field(
        False, description="Include location relations, defaults to False"
    )

    include_time_dependency: bool = Field(
        False, description="Include time dependency, defaults to False"
    )


class GetLocationOutput(BaseModel):
    """Model for the output of the location_details
      tool.

    This model provides the search results including both structured data
    and a formatted markdown representation for display purposes.
    """

    locations: Optional[List[Location]] = Field(
        None, description="Optional list of associated transformations"
    )

    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the search results in a human-readable format",
    )
