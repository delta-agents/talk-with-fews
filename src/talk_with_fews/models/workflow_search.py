"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List
from pydantic import BaseModel, Field


class WorkflowSearchResult(BaseModel):
    """Model representing a workflow search result."""

    id: int = Field(..., description="Unique identifier of the workflow")
    wf_id: str = Field(..., description="Name of the workflow")
    desc: str = Field(..., description="Description of the workflow")
    module_config_ids: List[str] = Field(
        ..., description="List of module configuration IDs in this workflow"
    )


class WorkflowSearchInput(BaseModel):
    """
    Input for workflow search.

    Attributes:
        name_pattern: Pattern to search for in workflow name or description
    """

    name_pattern: str = Field(
        ..., description="Pattern to search for in workflow name or description"
    )


class WorkflowSearchOutput(BaseModel):
    """Model for the output of the search_workflows tool."""

    results: List[WorkflowSearchResult] = Field(
        ..., description="List of matching workflows"
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the search results in a human-readable format",
    )
