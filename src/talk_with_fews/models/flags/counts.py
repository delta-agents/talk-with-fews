"""
Models for counting FEWS flag occurrences.
"""

from pydantic import BaseModel, Field


class FlagCount(BaseModel):
    """Count of a specific FEWS flag occurrence with its definition"""

    flag: int = Field(..., description="Flag number (0-9)")
    count: int = Field(..., description="Number of occurrences")
    percentage: float = Field(
        ..., description="Percentage of total values with this flag"
    )
    origin: str = Field(
        ..., description="Origin of the data (Original/Corrected/Completed)"
    )
    quality: str = Field(
        ..., description="Quality level (Reliable/Doubtful/Unreliable)"
    )
    description: str = Field(..., description="Detailed description of the flag")


class FlagCounts(BaseModel):
    """Counts of FEWS flags in the timeseries"""

    # Basic counts
    total_values: int = Field(..., description="Total number of values")
    missing_values: int = Field(..., description="Number of missing values (flag 9)")

    # Quality level counts from flags
    reliable_count: int = Field(
        ..., description="Number of reliable values (flag 0, 1, 2)"
    )
    doubtful_count: int = Field(
        ..., description="Number of doubtful values (flag 3, 4, 5)"
    )
    unreliable_count: int = Field(
        ..., description="Number of unreliable values (flag 6, 7, 8)"
    )

    # Quality level percentages
    reliable_percentage: float = Field(..., description="Percentage of reliable values")
    doubtful_percentage: float = Field(..., description="Percentage of doubtful values")
    unreliable_percentage: float = Field(
        ..., description="Percentage of unreliable values"
    )
