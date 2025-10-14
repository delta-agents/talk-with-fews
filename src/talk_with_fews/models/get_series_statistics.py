"""
Pydantic models for the get_series_headers tool.

This module defines the models used by the get_series_headers tool to retrieve
series statistics from the FEWS webservice with incremental caching.
"""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any

from pydantic_ai import ModelRetry
from talk_with_fews.models.base import LaxBaseModel


class GetSeriesStatisticsInput(LaxBaseModel):
    """
    GetSeriesStatisticsInput defines the input parameters for retrieving series statistics.

    Supports querying by parameter_id AND location_id for incremental caching.
    Can provide both basic statistics and interval analysis for comprehensive insights.

    This model can handle both object input and string input that represents a dict.
    """

    parameter_id: str = Field(
        ..., description="Parameter ID to retrieve series headers for (e.g., 'Kwel')"
    )
    location_id: str = Field(
        ..., description="Location ID to retrieve series headers for (e.g., 'GPG_1698')"
    )
    start_time: datetime = Field(
        description="Start date time for interval analysis (basic statistics ignore this and use full data range)"
    )
    end_time: datetime = Field(
        description="End date time for interval analysis (basic statistics ignore this and use full data range)"
    )
    include_interval_analysis: bool = Field(
        default=True,
        description="Whether to include interval analysis for temporal patterns (monthly, daily, etc.)",
    )
    interval_type: str = Field(
        default="MONTH",
        description="Interval type for temporal analysis: WEEK_DAY (group by day of week), CALENDAR_DAY (each calendar day), MONTH (group by month within year), CALENDAR_MONTH (group same month across years), YEAR (group by year). Only used when include_interval_analysis=True.",
    )

    @model_validator(mode="after")
    def validate_exclusive_fields(cls, values):
        parameter_id, location_id = values.parameter_id, values.location_id
        if not (parameter_id and location_id):
            raise ModelRetry("Both 'parameter_id' and 'location_id' must be provided.")
        return values


class GetSeriesStatisticsOutput(BaseModel):
    """
    GetSeriesStatisticsOutput provides comprehensive series statistics with interval analysis.

    Designed for cost optimization in AI applications while providing actionable information
    and enabling follow-up questions. Includes both basic statistics and temporal patterns.
    """

    description: str = Field(
        ...,
        description="Contextual description with data summary and actionable insights",
    )
    min_value: Optional[str] = Field(
        None,
        description="Minimum value across series (from full data range, not requested time range)",
    )
    max_value: Optional[str] = Field(
        None,
        description="Maximum value across series (from full data range, not requested time range)",
    )
    first_value_time: Optional[datetime] = Field(
        None, description="Earliest start date among series"
    )
    last_value_time: Optional[datetime] = Field(
        None, description="Latest end date among series"
    )
    # Interval analysis fields
    interval_analysis: Optional[Dict[str, Any]] = Field(
        None,
        description="Temporal analysis results including patterns by interval (monthly, daily, etc.)",
    )
    time_step: Optional[str] = Field(
        None,
        description="Time step description (e.g., 'Daily data', 'Hourly data', 'Data every 6 hours', 'Irregular time intervals (nonequidistant)')",
    )
    parameter_units: Optional[str] = Field(
        None, description="Parameter units (e.g., 'mm', 'm3/s', '°C')"
    )
    estimated_data_points_in_range: Optional[int] = Field(
        None,
        description="Estimated number of data points if get_series_data is called with the same start_time/end_time range (only for equidistant data)",
    )
