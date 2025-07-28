"""
Enhanced XML validation models for FEWS XML validation.

This module contains the data models for enhanced XML validation capabilities,
including auto-schema discovery, XPath evaluation, and comprehensive validation results.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """Individual validation error"""

    reason: str = Field(..., description="Error description")
    line: Optional[int] = Field(None, description="Line number where error occurred")
    column: Optional[int] = Field(
        None, description="Column number where error occurred"
    )
    element: Optional[str] = Field(None, description="Element that caused the error")


class ValidationWarning(BaseModel):
    """Individual validation warning"""

    reason: str = Field(..., description="Warning description")
    line: Optional[int] = Field(None, description="Line number where warning occurred")
    column: Optional[int] = Field(
        None, description="Column number where warning occurred"
    )
    element: Optional[str] = Field(None, description="Element that caused the warning")


class XPathResult(BaseModel):
    """Result of XPath evaluation"""

    element: str = Field(..., description="Element content as string")
    tag: str = Field(..., description="Element tag name")
    text: Optional[str] = Field(None, description="Element text content")
    attributes: Dict[str, str] = Field(
        default_factory=dict, description="Element attributes"
    )
    error: Optional[str] = Field(
        None, description="Error message if XPath evaluation failed"
    )


class SchemaInfo(BaseModel):
    """Information about the schema used for validation"""

    schema_url: str = Field(..., description="Schema file path")
    target_namespace: Optional[str] = Field(
        None, description="Target namespace of the schema"
    )
    version: Optional[str] = Field(None, description="Schema version")
    description: Optional[str] = Field(None, description="Schema description")
    root_elements: List[str] = Field(
        default_factory=list, description="Root elements defined in schema"
    )
    schema_type: str = Field(
        ..., description="Schema type (e.g., 'pi-schemas', 'adapter-schemas')"
    )


class ValidationSummary(BaseModel):
    """Summary of validation results"""

    total_elements: int = Field(..., description="Total number of elements in XML")
    validated_elements: int = Field(
        ..., description="Number of elements successfully validated"
    )
    error_count: int = Field(..., description="Number of validation errors")
    warning_count: int = Field(..., description="Number of validation warnings")
    validation_time_ms: float = Field(
        ..., description="Time taken for validation in milliseconds"
    )
    schema_load_time_ms: float = Field(
        ..., description="Time taken to load schema in milliseconds"
    )


class XMLValidationInput(BaseModel):
    """Enhanced input model for XML validation"""

    xml_content: str = Field(..., description="XML content to validate")
    schema_url: Optional[str] = Field(
        None, description="Specific schema URL or path. If None, auto-discover from XML"
    )
    xpath: Optional[str] = Field(
        None, description="XPath expression to validate specific elements"
    )
    validation_mode: str = Field(
        "lax", description="Validation mode: 'strict', 'lax', or 'skip'"
    )
    auto_discover_schema: bool = Field(
        True,
        description="Automatically discover appropriate schema if schema_url not provided",
    )
    include_schema_info: bool = Field(
        True, description="Include schema metadata in output"
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
    schema_info: Optional[SchemaInfo] = Field(None, description="Schema metadata")
    xpath_results: Optional[List[XPathResult]] = Field(
        None, description="XPath evaluation results"
    )
    validation_summary: ValidationSummary = Field(..., description="Summary statistics")
