"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Location


class GetLocationInput(BaseModel):
    """
    GetLocationInput defines the input parameters for retrieving location search results.

    Attributes:
        number_of_locations (Optional[int]): The maximum number of locations to retrieve.
        filter_locations_name (Optional[str]): An optional name filter for locations names, using the SQL LIKE functionality.

    This model allows flexible querying of location data, supporting both general and name-specific searches,
    and limiting the number of results returned.
    """

    number_of_locations: Optional[int] = Field(
        ..., description="Number of locations to retrieve"
    )
    filter_locations_name: Optional[str] = Field(
        None,
        description="Optional string used to filter the locations returned by using sql LIKE functionality",
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
