"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from talk_with_fews.models.base import Transformation

from talk_with_fews.models.base import TimeSeriesProperties



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
