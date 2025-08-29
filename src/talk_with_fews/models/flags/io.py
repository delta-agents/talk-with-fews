"""
Input/Output models for FEWS flag analysis.

These models define the input parameters and output structure.
"""

from datetime import datetime, timedelta
from typing import Dict, List

from pydantic import BaseModel, Field

from .counts import FlagCount, FlagCounts
from .definitions import FlagDefinition


class DateRange(BaseModel):
    """A period between two dates"""

    start: datetime = Field(..., description="Start of the period")
    end: datetime = Field(..., description="End of the period")
    duration: timedelta = Field(..., description="Duration of the period")


class SeriesFlagsInput(BaseModel):
    """Input parameters for flag analysis"""

    location_id: str = Field(..., description="Location ID to analyze")
    parameter_id: str = Field(..., description="Parameter ID to analyze")
    start_time: datetime = Field(..., description="Start time for analysis")
    end_time: datetime = Field(..., description="End time for analysis")
    include_flag_sources: bool = Field(
        False, description="Whether to request flag sources (requires FEWS API support)"
    )


class SeriesFlagsSummary(BaseModel):
    """Summary of FEWS flags in a timeseries"""

    # Basic information
    total_values: int = Field(..., description="Total number of values")
    # this was a date range, but we now use ISO 8601 strings as needs to be serializable
    start_date: str = Field(
        ..., description="Start date time of the analysis period in ISO 8601 format"
    )
    end_date: str = Field(
        ..., description="End date time of the analysis period in ISO 8601 format"
    )
    ## TODO: change above to and check it works
    # start_time: datetime = Field(..., description="Start time for analysis")
    # end_time: datetime = Field(..., description="End time for analysis")

    # Standard FEWS flag definitions
    flag_definitions: Dict[int, FlagDefinition] = Field(
        ..., description="Metadata about each flag type"
    )

    # Actual counts from timeseries
    flag_counts: List[FlagCount] = Field(
        ..., description="Count of each flag occurrence"
    )

    # Summary counts
    counts: FlagCounts = Field(..., description="Comprehensive count summary")
