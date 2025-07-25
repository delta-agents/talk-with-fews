"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series statistics from the FEWS webservice with incremental caching.
"""

from pydantic import BaseModel, Field
from typing import Optional


class GetSeriesStatisticsInput(BaseModel):
    """
    GetSeriesStatisticsInput defines the input parameters for retrieving series statistics.

    Supports querying by parameter_id OR location_id (not both) for incremental caching.
    """

    parameter_id: str = Field(
        ..., description="Parameter ID to retrieve series headers for (e.g., 'Kwel')"
    )
    location_id: str = Field(
        ...,
        description="Location ID to retrieve series headers for (e.g., 'GPG_1698')",
    )


class GetSeriesStatisticsOutput(BaseModel):
    """
    GetSeriesStatisticsOutput provides a minimal but meaningful response for series statistics.

    Designed for cost optimization in AI applications while providing actionable information
    and enabling follow-up questions.
    """

    count: int = Field(..., description="Total number of series found")
    description: Optional[str] = Field(
        None, description="Short description of the FEWS series or its context"
    )
    min_value: Optional[str] = Field(
        None, description="Minimum value across all series"
    )
    max_value: Optional[str] = Field(
        None, description="Maximum value across all series"
    )
    first_value_time: Optional[str] = Field(
        None, description="Earliest start date among all series (ISO 8601 format)"
    )
    last_value_time: Optional[str] = Field(
        None, description="Latest end date among all series (ISO 8601 format)"
    )
