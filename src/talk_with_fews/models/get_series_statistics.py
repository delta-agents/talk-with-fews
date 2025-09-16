"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series statistics from the FEWS webservice with incremental caching.
"""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional

from pydantic_ai import ModelRetry
from talk_with_fews.models.base import LaxBaseModel


class GetSeriesStatisticsInput(LaxBaseModel):
    """
    GetSeriesStatisticsInput defines the input parameters for retrieving series statistics.

    Supports querying by parameter_id AND location_id for incremental caching.

    This model can handle both object input and string input that represents a dict.
    """

    parameter_id: str = Field(
        ..., description="Parameter ID to retrieve series headers for (e.g., 'Kwel')"
    )
    location_id: str = Field(
        ..., description="Location ID to retrieve series headers for (e.g., 'GPG_1698')"
    )
    start_time: datetime = Field(description="Start date time of the analysis period")
    end_time: datetime = Field(description="End date time of the analysis period")

    @model_validator(mode="after")
    def validate_exclusive_fields(cls, values):
        parameter_id, location_id = values.parameter_id, values.location_id
        if not (parameter_id and location_id):
            raise ModelRetry("Both 'parameter_id' and 'location_id' must be provided.")
        return values


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
    min_value: Optional[str] = Field(None, description="Minimum value across series")
    max_value: Optional[str] = Field(None, description="Maximum value across series")
    first_value_time: Optional[datetime] = Field(
        None, description="Earliest start date among series "
    )
    last_value_time: Optional[datetime] = Field(
        None, description="Latest end date among series"
    )
