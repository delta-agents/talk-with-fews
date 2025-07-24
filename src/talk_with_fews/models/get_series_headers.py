"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series headers from the FEWS webservice with incremental caching.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class GetSeriesHeadersInput(BaseModel):
    """
    GetSeriesHeadersInput defines the input parameters for retrieving series headers.

    Supports querying by parameter_id OR location_id (not both) for incremental caching.
    """

    parameter_id: Optional[str] = Field(
        None, description="Parameter ID to retrieve series headers for (e.g., 'Kwel')"
    )
    location_id: Optional[str] = Field(
        None,
        description="Location ID to retrieve series headers for (e.g., 'GPG_1698')",
    )


class GetSeriesHeadersOutput(BaseModel):
    """
    GetSeriesHeadersOutput provides a minimal but meaningful response for series headers.

    Designed for cost optimization in AI applications while providing actionable information
    and enabling follow-up questions.
    """

    count: int = Field(..., description="Number of series found")
    summary: str = Field(..., description="Brief summary (max 200 chars)")
    sample_ids: List[str] = Field(..., description="First 3 series IDs for reference")
    available_filters: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Available values for user-friendly filtering options",
    )
    follow_up_suggestions: List[str] = Field(
        default_factory=list,
        description="User-friendly suggestions for next analysis steps (max 3)",
    )
