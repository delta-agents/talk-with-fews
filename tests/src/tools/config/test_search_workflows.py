from talk_with_fews.routers.setup_connections import get_runtime_ctx
from talk_with_fews.tools.config.workflow_search import search_workflows
from talk_with_fews.models import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
)
from tests.utils_tests import setup_dot_env
import asyncio


def test_search_workflows():
    user_settings = setup_dot_env()
    ctx = get_runtime_ctx(user_settings)
    workflow_search_input = WorkflowSearchInput(name_pattern="knmi")

    workflow_search_output: WorkflowSearchOutput = asyncio.run(
        search_workflows(ctx=ctx, input=workflow_search_input)
    )
    assert isinstance(workflow_search_output, WorkflowSearchOutput)
    assert workflow_search_output.results is not None
    assert len(workflow_search_output.results) > 0
