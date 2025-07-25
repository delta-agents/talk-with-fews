"""
Models for counting FEWS flag occurrences.

These models are used to track counts and percentages of flags.
They do NOT:
- Compute any patterns
- Analyze measurement values
- Set or modify flags
"""

from pydantic import BaseModel, Field


class FlagCount(BaseModel):
    """Count of a specific FEWS flag occurrence"""

    flag: int = Field(..., description="Flag number (0-9)")
    count: int = Field(..., description="Number of occurrences")
    percentage: float = Field(
        ..., description="Percentage of total values with this flag"
    )


class FlagCounts(BaseModel):
    """Counts of FEWS flags in the timeseries"""

    # Basic counts
    total_values: int = Field(..., description="Total number of values")
    missing_values: int = Field(..., description="Number of missing values (flag 9)")

    # Quality level counts from flags
    reliable_count: int = Field(..., description="Number of reliable values")
    doubtful_count: int = Field(..., description="Number of doubtful values")
    unreliable_count: int = Field(..., description="Number of unreliable values")

    # Quality level percentages
    reliable_percentage: float = Field(..., description="Percentage of reliable values")
    doubtful_percentage: float = Field(..., description="Percentage of doubtful values")
    unreliable_percentage: float = Field(
        ..., description="Percentage of unreliable values"
    )
