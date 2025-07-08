from pydantic import BaseModel, Field
from typing import Dict, List, Any

class DatabaseSchemaOutput(BaseModel):
    tables: Dict[str, List[str]] = Field(..., description="Table names and their columns")
    relationships: List[str] = Field(..., description="Table relationships")
    sample_data: Dict[str, Any] = Field(..., description="Sample data from the database")