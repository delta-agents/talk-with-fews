"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from talk_with_fews.models.base import Location


class GetLocationInput(BaseModel):
    """Model representing a location search result.

    A location search result extends the base time series properties with optional
    transformation information for search results.
    """

    number_of_locations: Optional[int] = Field(..., description="Number of locations to retrieve")
    query: Optional[str] = Field(
        None, description="Optional query string to filter locations"
    )
    locations_name: Optional[str] = Field(
        None, description="Optional name of the locations to filter by"
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
