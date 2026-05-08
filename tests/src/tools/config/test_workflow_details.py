from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.workflow_search import search_workflows
from talk_with_fews.tools.config.workflows_details import get_workflow_details
from talk_with_fews.models import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_get_workflow_details():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)

    # First search for a workflow to get a valid workflow_id
    workflow_search_input = WorkflowSearchInput(name_pattern="knmi")
    workflow_search_output: WorkflowSearchOutput = asyncio.run(
        search_workflows(ctx=ctx, input=workflow_search_input)
    )
    workflow_id = workflow_search_output.results[0].id

    workflow_details_input = WorkflowDetailsInput(workflow_id=workflow_id)
    workflow_details_output: WorkflowDetailsOutput = asyncio.run(
        get_workflow_details(ctx=ctx, input=workflow_details_input)
    )
    assert isinstance(workflow_details_output, WorkflowDetailsOutput)
