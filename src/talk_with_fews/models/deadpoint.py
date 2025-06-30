"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from talk_with_fews.models.base import ModuleSummary


class DeadPoint(BaseModel):
    """Model representing a dead point (unused time series) in the FEWS configuration."""

    id: int = Field(..., description="Unique identifier of the time series")
    modins: str = Field(..., description="Module instance that owns this time series")
    vtype: str = Field(..., description="Value type of the time series")
    parid: str = Field(..., description="Parameter identifier")
    qualifiers: str = Field(..., description="Additional qualifiers")
    tstype: str = Field(..., description="Type of time series")
    timess: str = Field(..., description="Time step")


class DeadPointProducer(BaseModel):
    """Model representing a transformation that produces a dead point."""

    tss_id: int = Field(..., description="ID of the time series")
    trafo_id: int = Field(..., description="ID of the transformation")
    trafo_desc: str = Field(..., description="Description of the transformation")
    module_instance: str = Field(
        ..., description="Module instance containing the transformation"
    )
    workflow_id: str = Field(..., description="ID of the workflow")


class DeadPointsAnalysisOutput(BaseModel):
    """Model for the output of the analyze_dead_points tool."""

    count: int = Field(..., description="Total number of dead points found")
    dead_points: List[DeadPoint] = Field(..., description="List of dead points")
    module_summary: List[ModuleSummary] = Field(
        ..., description="Summary of dead points by module"
    )
    unique_modules: int = Field(
        ..., description="Number of unique modules with dead points"
    )
    parameters_affected: int = Field(
        ..., description="Number of unique parameters affected"
    )
    producers: Optional[Dict[int, List[DeadPointProducer]]] = Field(
        None,
        description="Transformations producing dead points, grouped by time series ID",
    )
    recommendations: List[str] = Field(
        ..., description="List of recommendations for addressing dead points"
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the analysis results",
    )
