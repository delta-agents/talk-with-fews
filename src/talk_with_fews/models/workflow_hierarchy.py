"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from pydantic import Field
from talk_with_fews.models.base import LaxBaseModel


class WorkflowCallHierarchyInput(LaxBaseModel):
    """Model representing the details of a workflow call hierarchy.

    A workflow is a sequence of module instance calls that define a process in FEWS.
    The workflow call hierarchy provides a structured view of the workflows and their relationships.
    """

    root_workflow_id: int = Field(
        ..., description="Unique identifier of the root workflow"
    )
