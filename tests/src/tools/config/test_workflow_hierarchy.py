from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.workflow_search import search_workflows
from talk_with_fews.tools.config.workflow_hierarchy import find_workflow_call_hierarchy
from talk_with_fews.models import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
    WorkflowCallHierarchyInput,
    SQLQueryOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_find_workflow_call_hierarchy():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)

    # First search for a workflow to get a valid root_workflow_id
    workflow_search_input = WorkflowSearchInput(name_pattern="knmi")
    workflow_search_output: WorkflowSearchOutput = asyncio.run(
        search_workflows(ctx=ctx, input=workflow_search_input)
    )
    root_workflow_id = workflow_search_output.results[0].id

    workflow_call_hierarchy_input = WorkflowCallHierarchyInput(
        root_workflow_id=root_workflow_id,
    )
    workflow_call_hierarchy_output: SQLQueryOutput = asyncio.run(
        find_workflow_call_hierarchy(ctx=ctx, input=workflow_call_hierarchy_input)
    )
    assert isinstance(workflow_call_hierarchy_output, SQLQueryOutput)
