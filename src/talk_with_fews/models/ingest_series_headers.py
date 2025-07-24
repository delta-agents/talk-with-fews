"""
Pydantic models for the ingest_series_headers tool.

This module defines the models used by the ingest_series_headers tool to fetch
and store series headers from the FEWS webservice into the local DuckDB cache.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class IngestSeriesHeadersInput(BaseModel):
    """
    IngestSeriesHeadersInput defines the input parameters for ingesting series headers.

    Supports both parameter-based and location-based queries to the FEWS webservice.
    """

    parameter_id: Optional[str] = Field(
        None, description="Parameter ID to ingest series headers for (e.g., 'Kwel')"
    )
    location_id: Optional[str] = Field(
        None, description="Location ID to ingest series headers for (e.g., 'GPG_1698')"
    )


class IngestSeriesHeadersOutput(BaseModel):
    """
    IngestSeriesHeadersOutput provides status and examples for the ingestion process.

    Includes SQL examples for querying the ingested data and status information.
    """

    description: str = Field(
        ..., description="Description of the ingestion process and results"
    )
    series_count: int = Field(..., description="Number of series headers ingested")
    sql_examples: List[str] = Field(
        ..., description="List of SQL examples to query the ingested data"
    )
