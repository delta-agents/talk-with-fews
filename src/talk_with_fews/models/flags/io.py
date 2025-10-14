"""
Input/Output models for FEWS flag analysis.

These models define the input parameters and output structure.
"""

from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel, Field

from .counts import FlagCount, FlagCounts


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


class SeriesFlagsOutput(BaseModel):
    """Output model for FEWS flag analysis tool.

    This model provides flag analysis results optimized for LLM consumption with
    structured data and actionable contextual description.
    """

    # Core information - lean and mean like GetSeriesHeadersOutput
    description: str = Field(
        ...,
        description="Contextual description with actionable insights for data quality assessment",
    )

    # Essential flag analysis data (includes flag definitions)
    flag_counts: List[FlagCount] = Field(
        ...,
        description="Count of each flag occurrence with percentages and flag definitions",
    )

    # Summary statistics
    counts: FlagCounts = Field(
        ...,
        description="Comprehensive count summary (total, reliable, doubtful, unreliable counts and percentages)",
    )
