"""
Base models for FEWS flag definitions.

These models define the structure of FEWS quality flags and their sources.
They do NOT:
- Compute any patterns
- Analyze measurement values
- Set or modify flags
"""

from pydantic import BaseModel, Field


class FlagDefinition(BaseModel):
    """Standard FEWS flag definition"""

    flag: int = Field(..., description="Flag number (0-9)")
    origin: str = Field(
        ..., description="Origin of the data (Original/Corrected/Completed)"
    )
    quality: str = Field(
        ..., description="Quality level (Reliable/Doubtful/Unreliable)"
    )
    description: str = Field(..., description="Detailed description of the flag")


class FlagSourceDefinition(BaseModel):
    """Standard FEWS flag source definition"""

    code: str = Field(..., description="Source code (e.g., 'IMP', 'SN', 'HN', etc.)")
    description: str = Field(..., description="Description of the flag source")
    validation_type: str = Field(
        ...,
        description="Type of validation (primary/secondary/custom)",
        example="primary",
    )
