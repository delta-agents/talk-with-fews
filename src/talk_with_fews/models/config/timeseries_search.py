"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from talk_with_fews.models.base import (
    Transformation,
    TimeSeriesProperties,
    LaxBaseModel,
)


class TimeSeriesSearchInput(LaxBaseModel):
    """Model for the input of the search_timeseries tool.

    This model defines the parameters to search for time series.

    Attributes:
        parameter_id: Optional pattern to search for in parameter ID
        qualifier_pattern: Optional pattern to search for in qualifier
        module_instance: Optional pattern to search for in module instance
        endpoint: Optional filter for endpoint status
        include_transformations: Whether to include transformation information
    """

    parameter_id: Optional[str] = Field(
        None, description="Pattern to search for in parameter ID"
    )
    qualifier_pattern: Optional[str] = Field(
        None, description="Pattern to search for in qualifier"
    )
    module_instance: Optional[str] = Field(
        None, description="Pattern to search for in module instance"
    )
    endpoint: Optional[bool] = Field(
        None,
        description="Filter by endpoint status (True for endpoints, False for non-endpoints)",
    )
    include_transformations: bool = Field(
        False, description="Whether to include transformation information"
    )


class TimeSeriesSearchResult(TimeSeriesProperties):
    """Model representing a time series search result.

    A time series search result extends the base time series properties with optional
    transformation information for search results.
    """

    transformations: Optional[List[Transformation]] = Field(
        None, description="Optional list of associated transformations"
    )


class TimeSeriesSearchOutput(BaseModel):
    """Model for the output of the search_timeseries tool.

    This model provides the search results including both structured data
    and a formatted markdown representation for display purposes.
    """

    results: List[TimeSeriesSearchResult] = Field(
        ..., description="List of matching time series"
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the search results in a human-readable format",
    )
