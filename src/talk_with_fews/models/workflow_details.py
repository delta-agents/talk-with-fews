"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from pydantic import BaseModel, Field, List

from talk_with_fews.models.base import ModuleInstanceCall


class WorkflowDetails(BaseModel):
    """Model representing the details of a workflow.

    A workflow is a sequence of module instance calls that define a process in FEWS.
    """

    id: int = Field(..., description="Unique identifier of the workflow")
    wf_id: str = Field(..., description="Name of the workflow")
    desc: str = Field(..., description="Description of the workflow's purpose")
    wffn: str = Field(..., description="Workflow function name")
    module_calls: List[ModuleInstanceCall] = Field(
        ..., description="List of module instance calls in this workflow"
    )

class WorkflowDetailsInput(BaseModel):
    """Model for the input of the get_workflow_details tool.

    This model defines the required parameters to get details about a specific workflow.

    Attributes:
        workflow_id: The unique identifier of the workflow to describe
    """

    workflow_id: int = Field(
        ..., description="The unique identifier of the workflow to describe"
    )

class WorkflowDetailsOutput(BaseModel):
    """Model for the output of the get_workflow_details tool.

    This model provides a complete description of a workflow, including both its structured data
    and a formatted markdown representation for display purposes.
    """

    results: List[WorkflowDetails] = Field(
        ...,
        description="List containing the workflow details and its associated module calls",
    )
    markdown_content: str = Field(
        ...,
        description="Pre-formatted markdown string that displays the workflow information in a human-readable format",
    )

