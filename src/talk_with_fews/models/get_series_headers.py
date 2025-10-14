"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series headers from the FEWS webservice with incremental caching.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import ModelRetry
from talk_with_fews.models.base import LaxBaseModel


class GetSeriesHeadersInput(LaxBaseModel):
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
    """Model for the output of the get_series_headers tool.

    This model provides search results optimized for LLM consumption with
    structured data and actionable contextual description.
    """

    series_headers: List[Dict[str, Any]] = Field(
        ...,
        description="List of series headers with key information (location_id, parameter_id, parameter_name, location_name, time_step_unit, time_step_multiplier, module_instance_id, type, parameter_unit)",
    )
    description: str = Field(
        ...,
        description="Contextual description with actionable insights for follow-up analysis",
    )
    available_ids: Dict[str, List[str]] = Field(
        ...,
        description="Available IDs for follow-up queries: 'locations' for parameter queries, 'parameters' for location queries",
    )
