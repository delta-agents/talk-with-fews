"""
Pydantic models for the get_series_statistics tool.

This module defines the models used by the get_series_statistics tool to retrieve
series statistics from the FEWS webservice with incremental caching.
"""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Dict, Any, Union, List
from enum import Enum

from pydantic_ai import ModelRetry
from talk_with_fews.models.base import LaxBaseModel


class IntervalType(str, Enum):
    """Interval types for temporal analysis."""

    WEEK_DAY = "WEEK_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"
    MONTH = "MONTH"
    CALENDAR_MONTH = "CALENDAR_MONTH"
    YEAR = "YEAR"


class GetSeriesStatisticsInput(LaxBaseModel):
    """
    GetSeriesStatisticsInput defines the input parameters for retrieving series statistics.

    Requires a valid parameter_id + location_id combination that exists in the FEWS service.
    Use get_series_headers to find valid combinations before calling this function.

    Supports querying by parameter_id AND location_id for incremental caching.
    Can provide both data summary and interval analysis for comprehensive insights.
    Optional moduleInstanceId allows filtering to a specific module instance.

    This model can handle both object input and string input that represents a dict.
    """

    parameter_id: Union[str, List[str]] = Field(
        ...,
        description="Parameter ID(s) - can be a single ID string or list of IDs (use get_series_headers to find valid combinations)",
    )
    location_id: Union[str, List[str]] = Field(
        ...,
        description="Location ID(s) - can be a single ID string or list of IDs (use get_series_headers to find valid combinations)",
    )
    module_instance_id: Optional[str] = Field(
        None,
        description="Optional module instance ID to filter to a specific series (use get_series_headers to find available moduleInstanceIds)",
    )
    start_time: datetime = Field(
        description="Start date time for interval analysis (data summary uses full available range, not this range)"
    )
    end_time: datetime = Field(
        description="End date time for interval analysis (data summary uses full available range, not this range)"
    )
    include_interval_analysis: bool = Field(
        default=True,
        description="Whether to include interval analysis for temporal patterns (monthly, daily, etc.)",
    )
    interval_type: IntervalType = Field(
        default=IntervalType.MONTH,
        description="Interval type for temporal analysis. Only used when include_interval_analysis=True.",
    )

    @model_validator(mode="after")
    def validate_exclusive_fields(cls, values):
        parameter_id, location_id = values.parameter_id, values.location_id

        # Convert to lists for easier processing
        if isinstance(parameter_id, str):
            param_list = [parameter_id.strip()] if parameter_id.strip() else []
        else:
            param_list = parameter_id if parameter_id else []

        if isinstance(location_id, str):
            loc_list = [location_id.strip()] if location_id.strip() else []
        else:
            loc_list = location_id if location_id else []

        if not param_list or not loc_list:
            raise ModelRetry("Both 'parameter_id' and 'location_id' must be provided.")

        # Check that we don't have multiple of both - only one can be a list with multiple items
        param_is_multiple = len(param_list) > 1
        loc_is_multiple = len(loc_list) > 1

        if param_is_multiple and loc_is_multiple:
            raise ModelRetry(
                "Cannot specify multiple parameter_ids AND multiple location_ids. Choose one to be multiple and the other to be single."
            )

        return values


class SeriesStatisticsItem(BaseModel):
    """
    SeriesStatisticsItem represents statistics for a single series.

    Provides data characteristics (min/max values, units, count), time information
    (data range, time step), and interval statistics (monthly/daily patterns) to
    help decide whether to call get_series_data for detailed analysis.
    """

    # Core data summary
    description: str = Field(
        ...,
        description="Contextual description with data summary and actionable insights",
    )

    # Data characteristics
    min_value: Optional[str] = Field(
        None,
        description="Minimum value across series (from requested time range)",
    )
    max_value: Optional[str] = Field(
        None,
        description="Maximum value across series (from requested time range)",
    )
    parameter_units: Optional[str] = Field(
        None, description="Parameter units (e.g., 'mm', 'm3/s', '°C')"
    )

    # Time information
    first_value_time: Optional[datetime] = Field(
        None, description="Earliest data point timestamp in the series"
    )
    last_value_time: Optional[datetime] = Field(
        None, description="Latest data point timestamp in the series"
    )
    time_step: Optional[str] = Field(
        None,
        description="Time step description (e.g., 'Daily data', 'Hourly data', 'Data every 6 hours', 'Irregular time intervals (nonequidistant)')",
    )
    timestep_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw timestep information: {'unit': str, 'multiplier': int}",
    )

    # Analysis and estimation
    interval_analysis: Optional[Dict[str, Any]] = Field(
        None,
        description="Temporal analysis results including patterns by interval (monthly, daily, etc.)",
    )
    estimated_data_points_in_range: Optional[int] = Field(
        None,
        description="Estimated number of data points if get_series_data is called with the same start_time/end_time range (only for equidistant data)",
    )

    # Series identification
    location_id: Optional[str] = Field(
        None,
        description="Location ID for this specific series",
    )
    parameter_id: Optional[str] = Field(
        None,
        description="Parameter ID for this specific series",
    )
    module_instance_id: Optional[str] = Field(
        None,
        description="Module instance ID that manages this specific series",
    )


class GetSeriesStatisticsOutput(BaseModel):
    """Model for the output of the get_series_statistics tool.

    This model provides search results optimized for LLM consumption with
    structured data and actionable contextual description.
    """

    series_statistics: List[SeriesStatisticsItem] = Field(
        ...,
        description="List of series statistics with key information for each series",
    )
    description: str = Field(
        ...,
        description="Contextual description with actionable insights for follow-up analysis",
    )
