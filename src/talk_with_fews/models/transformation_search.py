"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from talk_with_fews.models.base import LaxBaseModel


class TransformationSearchResult(BaseModel):
    """Model representing a transformation search result.

    A transformation search result includes the transformation details and its context
    within a workflow and module configuration.
    """

    id: int = Field(..., description="Unique identifier of the transformation")
    desc: str = Field(..., description="Description of what the transformation does")
    ord_nr: int = Field(
        ...,
        description="Order number indicating the sequence in the module configuration",
    )
    mic_id: int = Field(
        ..., description="Unique identifier of the module configuration"
    )
    modins: str = Field(
        ..., description="Name of the module instance containing this transformation"
    )
    workflow_id: int = Field(..., description="Unique identifier of the workflow")
    workflow_name: str = Field(..., description="Name of the workflow")
    workflow_desc: str = Field(..., description="Description of the workflow")


class TransformationSearchInput(LaxBaseModel):
    """Model for the input of the search_transformations tool.

    This model defines the parameters to search for transformations.

    Attributes:
        description_pattern: Pattern to search for in transformation description
        workflow_name: Optional pattern to filter by workflow name
        module_config: Optional pattern to filter by module configuration name
        max_depth: Optional maximum depth for hierarchical results
    """

    description_pattern: str = Field(
        ..., description="Pattern to search for in transformation description"
    )
    workflow_name: Optional[str] = Field(
        None, description="Optional pattern to filter by workflow name"
    )
    module_config: Optional[str] = Field(
        None, description="Optional pattern to filter by module configuration name"
    )
    max_depth: Optional[int] = Field(
        None, description="Optional maximum depth for hierarchical results"
    )


class TransformationSearchOutput(BaseModel):
    """Model for the output of the search_transformations tool.

    This model provides the search results including both structured data
    and a formatted markdown representation for display purposes.
    """

    results: List[TransformationSearchResult] = Field(
        ..., description="List of matching transformations with their context"
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the search results in a human-readable format",
    )
