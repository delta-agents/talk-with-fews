"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ParameterDetailsInput(BaseModel):
    """Model representing a parameter search result.

    A parameter search result extends the base time series properties with optional
    transformation information for search results.
    """

    show_attributes: Optional[bool] = Field(
        ..., description="Show parameter attributes"
    )
    documentFormat: Optional[str] = Field(
        ..., description="Format for the output document: PI_JSON or PI_XML")



class ParameterDetailsOutput(BaseModel):
    """Model for the output of the parameter_details
      tool.

    This model provides the search results including both structured data
    and a formatted markdown representation for display purposes.
    """

