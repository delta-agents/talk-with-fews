"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from talk_with_fews.models.base import LaxBaseModel


class DependencyAnalysisOutput(BaseModel):
    """Model for the output of the analyze_dependencies tool.

    This model provides a complete description of dependencies, including both structured data
    and a formatted markdown representation for display purposes.
    """

    results: List[Dict[str, Any]] = Field(
        ..., description="List containing the dependency analysis results"
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the dependency information in a human-readable format",
    )


class DependencyAnalysisInput(LaxBaseModel):
    """Model for the input of the analyze_dependencies tool.

    This model defines the required parameters to analyze dependencies.

    Attributes:
        entity_type: Type of entity to analyze (timeseries, transformation, workflow)
        entity_id: ID of the entity to analyze
        direction: Direction of dependencies to analyze (upstream, downstream, or both)
    """

    entity_type: str = Field(
        ...,
        description="Type of entity to analyze (timeseries, transformation, workflow)",
    )
    entity_id: int = Field(..., description="ID of the entity to analyze")
    direction: str = Field(
        "both",
        description="Direction of dependencies to analyze (upstream, downstream, or both)",
    )
