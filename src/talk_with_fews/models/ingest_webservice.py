from typing import List
from pydantic import BaseModel, Field


class IngestLocationsOutput(BaseModel):
    """
    Represents the output of the ingest locations process.
    Attributes:
        description (str): Description of the ingestion process.
        sql_examples (List[str]): List of SQL examples to query the ingested data.
    """

    description: str = Field(..., description="Description of the ingestion process")
    sql_examples: List[str] = Field(
        ..., description="List of SQL examples to query the ingested data"
    )


class IngestParameterOutput(BaseModel):
    """
    Represents the output of the ingest Parameter process.
    Attributes:

        description (str): Description of the ingestion process.
        sql_examples (List[str]): List of SQL examples to query the ingested data.
    """

    description: str = Field(
        ...,
        description="Description of the ingestion process",
    )
    sql_examples: List[str] = Field(
        ..., description="List of SQL examples to query the ingested data"
    )
