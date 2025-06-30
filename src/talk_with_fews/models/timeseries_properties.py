"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from talk_with_fews.models.base import Transformation


class TimeSeriesProperties(BaseModel):
    """Model representing the core properties of a time series in the FEWS configuration.

    A time series is a sequence of data points indexed in time order. In FEWS, each time series
    has specific properties that define its characteristics and how it's used in the system.
    """

    id: int = Field(..., description="Unique identifier of the time series")
    modins: str = Field(
        ..., description="Module instance that owns or manages this time series"
    )
    vtype: str = Field(
        ..., description="Value type of the time series (e.g., 'scalar', 'vector')"
    )
    parid: str = Field(
        ..., description="Parameter identifier (e.g., 'bodemvocht_e' for soil moisture)"
    )
    qualifiers: str = Field(
        ...,
        description="Additional qualifiers that specify the time series (e.g., '30cm_minmv' for 30cm minimum value)",
    )
    tstype: str = Field(
        ..., description="Type of time series (e.g., 'external historical', 'internal')"
    )
    timess: str = Field(
        ..., description="Time step of the time series (e.g., '10minute', '1hour')"
    )
    description: str = Field(
        ...,
        description="Formatted string describing the time series using the standard template",
    )
    endpoint: bool = Field(False, description="Whether this time series is an endpoint")
    endpoint_desc: Optional[str] = Field(
        None, description="Endpoint description if the time series is an endpoint"
    )
    transformations: Optional[List[Transformation]] = Field(
        None,
        description="Optional list of transformations that use this time series as input or output",
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
