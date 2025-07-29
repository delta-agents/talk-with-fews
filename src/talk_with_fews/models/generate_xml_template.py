"""
Models for XML template generation.

This module contains the data models for XML template generation capabilities
using xmlschema package.
"""

from typing import Optional
from pydantic import BaseModel, Field


class XMLTemplateInput(BaseModel):
    """Input model for XML template generation"""

    schema_url: str = Field(..., description="Path to the XSD schema file")
    root_element: Optional[str] = Field(
        None,
        description="Specific root element to generate template for (if None, uses first available)",
    )
    include_optional: bool = Field(
        True, description="Whether to include optional elements in the template"
    )
    include_attributes: bool = Field(
        True, description="Whether to include attributes in the template"
    )


class XMLTemplateOutput(BaseModel):
    """Output model for XML template generation"""

    template: str = Field(..., description="Generated XML template")
    schema_location: str = Field(
        ..., description="Schema file used for template generation"
    )
    root_element: str = Field(..., description="Root element of the generated template")
    includes_optional: bool = Field(
        ..., description="Whether optional elements were included"
    )
    includes_attributes: bool = Field(
        ..., description="Whether attributes were included"
    )
