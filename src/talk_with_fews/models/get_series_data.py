from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TimeseriesValue(BaseModel):
    datetime: datetime
    location_id: str
    station_name: str
    parameter_id: str
    moduleinstance_id: str
    value: Optional[float]  # Optional to handle None for missing values
    flag: int


class GetSeriesDataInput(BaseModel):
    location_id: str = Field(..., description="Location ID to fetch data for")
    parameter_id: str = Field(..., description="Parameter ID to fetch data for")
    start_time: datetime = Field(..., description="Start time for data retrieval")
    end_time: datetime = Field(..., description="End time for data retrieval")


class GetSeriesDataOutput(BaseModel):
    values: List[TimeseriesValue]
    metadata: dict  # Contains header information like units, coordinates, etc.
    csv_data: str  # CSV formatted string with the specified columns
