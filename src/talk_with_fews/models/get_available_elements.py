"""
Models for getting available elements from FEWS schemas.

This module contains the data models for retrieving available elements
from FEWS XSD schemas with pagination support.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from .fews_schema_options import FEWSSchemaOption


class GetAvailableElementsInput(BaseModel):
    """Input model for getting available elements from a schema"""

    schema_option: FEWSSchemaOption = Field(
        ..., description="FEWS schema option to get available elements from"
    )
    root_element: Optional[str] = Field(
        None,
        description="Specific root element to search in (if None, uses first available)",
    )
    target_element: Optional[str] = Field(
        None,
        description="Specific sub-element to search within (if None, searches entire schema)",
    )
    limit: Optional[int] = Field(
        20, description="Maximum number of elements to return (default: 20, max: 100)"
    )
    offset: Optional[int] = Field(
        0, description="Number of elements to skip (for pagination, default: 0)"
    )


class GetAvailableElementsOutput(BaseModel):
    """Output model for getting available elements from a schema"""

    schema_location: str = Field(..., description="Location of the schema file used")
    root_element: str = Field(..., description="Root element name used for search")
    target_element: Optional[str] = Field(
        None, description="Target sub-element that was searched within"
    )
    available_elements: List[str] = Field(
        ..., description="List of available element names"
    )
    total_count: int = Field(..., description="Total number of available elements")
    limit: int = Field(..., description="Number of elements returned in this response")
    offset: int = Field(..., description="Number of elements skipped")
    has_more: bool = Field(..., description="Whether there are more elements available")
    next_offset: Optional[int] = Field(
        None, description="Offset for next page (if has_more is True)"
    )
