"""Models for retrieving timeseries data from FEWS."""

from datetime import datetime
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field
from talk_with_fews.models.base import LaxBaseModel


class TimeseriesValue(BaseModel):
    """Single measurement point in a time series."""

    datetime: Annotated[
        datetime,
        Field(
            description="When the measurement was taken (use for time-based analysis and plotting)"
        ),
    ]
    value: Optional[float] = Field(
        None,
        description="The measured value (None indicates missing/bad data - filter out for analysis)",
    )
    flag: int = Field(
        ...,
        description="Data quality indicator: 0=good data, >0 indicates issues (filter on flag=0 for clean analysis)",
    )
    flag_source: Optional[str] = Field(
        None,
        description="Origin of quality issue (e.g., 'IMP'=interpolated, 'SN'=sensor noise, 'HX'=human error)",
    )


class GetSeriesDataInput(LaxBaseModel):
    """Retrieve time series measurements from a specific location and parameter.

    Use this to get actual measurement data for analysis, visualization, and reporting.
    Supports flexible date formats and automatic handling of large datasets.
    """

    location_id: str = Field(
        ..., description="Location identifier (e.g., 'beg_109', 'VOV9345')"
    )
    parameter_id: str = Field(
        ..., description="Parameter identifier (e.g., 'BG.b.0', 'WNSHDB1')"
    )
    start_time: datetime = Field(
        description="Start date/time for the time series (accepts '2024-01-01' or '2024-01-01T00:00:00')"
    )
    end_time: datetime = Field(
        description="End date/time for the time series (accepts '2024-01-07' or '2024-01-07T23:59:59')"
    )
    include_flag_sources: bool = Field(
        False,
        description="Include flag source information (e.g., 'IMP', 'SN') for data quality analysis",
    )


class GetSeriesDataOutput(BaseModel):
    """Time series data ready for analysis, visualization, and export."""

    values: List[TimeseriesValue] = Field(
        ...,
        description="Time series measurements: timestamps, values, and quality flags for analysis and plotting",
    )
    metadata: dict = Field(
        ...,
        description="Station information: location details, parameter info, units, coordinates. Includes thinning info when large datasets are automatically reduced for performance.",
    )
