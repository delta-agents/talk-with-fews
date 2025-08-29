from pydantic import BaseModel, Field
from typing import Dict, List, Any

from talk_with_fews.models.base import LaxBaseModel


class DatabaseSchemaInput(LaxBaseModel):
    """
    Input model for get_database_schema tool.
    Currently, no parameters are required, but this can be extended in the future.
    """


class DatabaseSchemaOutput(BaseModel):
    tables: Dict[str, List[str]] = Field(
        ..., description="Table names and their columns"
    )
    relationships: List[str] = Field(..., description="Table relationships")
    sample_data: Dict[str, Any] = Field(
        ..., description="Sample data from the database"
    )
