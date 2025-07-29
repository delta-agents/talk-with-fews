"""
Models for XML template generation.

This module contains the data models for XML template generation capabilities
using xmlschema package.
"""

from typing import Optional
from pydantic import BaseModel, Field
from .fews_schema_options import FEWSSchemaOption


class XMLTemplateInput(BaseModel):
    """Input model for XML template generation"""

    schema_option: FEWSSchemaOption = Field(
        ..., description="FEWS schema option to use for template generation"
    )
    root_element: Optional[str] = Field(
        None,
        description="Specific root element to generate template for (if None, uses first available)",
    )
    target_element: Optional[str] = Field(
        None,
        description="Specific sub-element to generate template for (e.g., 'general', 'timeSeriesSet'). If specified, generates only this element's template.",
    )
    include_optional: bool = Field(
        False, description="Whether to include optional elements in the template"
    )
    include_attributes: bool = Field(
        True, description="Whether to include attributes in the template"
    )


class XMLTemplateOutput(BaseModel):
    """Output model for XML template generation"""

    template: str = Field(..., description="Generated XML template")
    schema_location: str = Field(..., description="Location of the schema file used")
    root_element: str = Field(..., description="Root element name used for generation")
    target_element: Optional[str] = Field(
        None, description="Target sub-element that was generated (if partial template)"
    )
    includes_optional: bool = Field(
        ..., description="Whether optional elements were included"
    )
    includes_attributes: bool = Field(
        ..., description="Whether attributes were included"
    )
