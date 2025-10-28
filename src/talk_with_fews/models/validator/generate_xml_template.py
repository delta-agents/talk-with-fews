"""
Models for XML template generation.

This module contains the data models for XML template generation capabilities
using xmlschema package.
"""

from typing import Optional
from pydantic import BaseModel, Field
from talk_with_fews.models.validator.fews_schema_options import FEWSSchemaOption
from talk_with_fews.models.base import LaxBaseModel


class XMLTemplateInput(LaxBaseModel):
    """Input model for XML template generation"""

    schema_option: FEWSSchemaOption = Field(
        ..., description="FEWS schema option to use for template generation"
    )
    root_element: Optional[str] = Field(
        None,
        description="Specific root element to generate template for (if None, uses first available)",
    )
    target_element: str = Field(
        ...,
        description="Specific sub-element to generate template for (e.g., 'general', 'timeSeriesSet'). This field is required to prevent long-running operations.",
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
    target_element: str = Field(
        ..., description="Target sub-element that was generated"
    )
    includes_optional: bool = Field(
        ..., description="Whether optional elements were included"
    )
    includes_attributes: bool = Field(
        ..., description="Whether attributes were included"
    )
