from datetime import datetime
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field


class TimeseriesValue(BaseModel):
    datetime: Annotated[
        datetime,
        Field(
            description="Timestamp of the measurement (combination of date and time)"
        ),
    ]
    location_id: str = Field(
        ..., description="Unique identifier of the measurement location"
    )
    station_name: str = Field(
        ..., description="Human-readable name of the measurement station"
    )
    parameter_id: str = Field(
        ..., description="Identifier of the measured parameter (e.g., 'Kwel', 'Eref.d')"
    )
    moduleinstance_id: str = Field(
        ...,
        description="Identifier of the FEWS module instance that produced this data",
    )
    value: Optional[float] = Field(
        None,
        description="Measured value. None if the measurement equals the missVal from XML",
    )
    flag: int = Field(
        ...,
        description="Quality flag for the measurement (0 = good, other values indicate specific issues)",
    )


class GetSeriesDataInput(BaseModel):
    location_id: str = Field(..., description="Location ID to fetch data for")
    parameter_id: str = Field(..., description="Parameter ID to fetch data for")
    start_time: Annotated[datetime, Field(description="Start time for data retrieval")]
    end_time: Annotated[datetime, Field(description="End time for data retrieval")]


class GetSeriesDataOutput(BaseModel):
    values: List[TimeseriesValue] = Field(
        ..., description="List of timeseries values with their associated metadata"
    )
    metadata: dict = Field(
        ...,
        description="Header information from the XML response including units, coordinates, and other metadata",
    )
    csv_data: str = Field(
        ...,
        description="CSV formatted string containing the timeseries data with columns: datetime, location-id, station-name, parameter-id, moduleinstance-id, value, flag",
    )
