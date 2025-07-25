"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series headers from the FEWS webservice with incremental caching.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import ModelRetry


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

    @model_validator(mode="after")
    def validate_exclusive_fields(cls, values):
        parameter_id, location_id = (
            values.parameter_id,
            values.location_id,
        )
        if not (parameter_id or location_id):
            raise ModelRetry("Either 'parameter_id' or 'location_id' must be provided.")
        if parameter_id and location_id:
            raise ModelRetry(
                "Only one of 'parameter_id' or 'location_id' can be provided, not both."
            )
        return values


class GetSeriesHeadersOutput(BaseModel):
    """
    GetSeriesHeadersOutput provides a minimal but meaningful response for series headers.

    Designed for cost optimization in AI applications while providing actionable information
    and enabling follow-up questions.
    """

    count: int = Field(..., description="Number of series found")
    summary: str = Field(..., description="Brief summary (max 200 chars)")
    sample_ids: str = Field(
        ..., description="First 5 series IDs for reference in markdown format"
    )
    available_filters: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Available values for user-friendly filtering options",
    )
    follow_up_suggestions: List[str] = Field(
        default_factory=list,
        description="User-friendly suggestions for next analysis steps (max 3)",
    )
