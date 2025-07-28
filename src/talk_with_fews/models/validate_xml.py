"""
Enhanced XML validation models for FEWS XML validation.

This module contains the data models for enhanced XML validation capabilities,
including auto-schema discovery and validation results.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """Individual validation error"""

    reason: str = Field(..., description="Error description")
    xpath: Optional[str] = Field(
        None, description="Debug information about element discovery path"
    )


class ValidationWarning(BaseModel):
    """Individual validation warning"""

    reason: str = Field(..., description="Warning description")


class XMLValidationInput(BaseModel):
    """Enhanced input model for XML validation"""

    xml_content: str = Field(..., description="XML content to validate")
    schema_url: Optional[str] = Field(
        None, description="Specific schema URL or path. If None, auto-discover from XML"
    )
    validation_mode: str = Field(
        "lax", description="Validation mode: 'strict', 'lax', or 'skip'"
    )


class XMLValidationOutput(BaseModel):
    """Enhanced output model for XML validation results"""

    is_valid: bool = Field(..., description="Whether XML is valid")
    errors: List[ValidationError] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[ValidationWarning] = Field(
        default_factory=list, description="List of validation warnings"
    )
    schema_location: Optional[str] = Field(
        None, description="Schema file used for validation"
    )
