from pydantic_ai import RunContext, ModelRetry

from talk_with_fews.models.config.sql_query import SQLQueryInput
from talk_with_fews.models.base import Deps

from talk_with_fews.models.config.workflow_details import (
    WorkflowDetails,
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from talk_with_fews.tools.config.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def get_workflow_details(
    ctx: RunContext[Deps], input: WorkflowDetailsInput
) -> WorkflowDetailsOutput:
    """
    Get detailed information about a specific workflow, including its module instance calls
    and their transformations in sequential order.

    Args:
        ctx: RunContext with database connection
        input: WorkflowDetailsInput containing the workflow ID

    Returns:
        WorkflowDetailsOutput: A complete description of the workflow including:
            - Structured data about the workflow and its module calls
            - Pre-formatted markdown content for display
    """
    # Get workflow details, module calls, and their transformations
    query = f"""
    SELECT cs.id, cs.wf_id, cs.description, cs.wffn,
           mc.id as mic_id, mc.modins,
           t.idx as trafo_idx, t.description as trafo_desc, t.ord_nr
    FROM call_stacks cs
    LEFT JOIN modins_calls mc ON cs.id = mc.call_stack_id
    LEFT JOIN trafos t ON mc.id = t.mic_id
    WHERE cs.id = {input.workflow_id}
    ORDER BY mc.id, t.ord_nr
    """

    result = await execute_query(ctx, SQLQueryInput(query=query))

    if not result.results:
        raise ModelRetry(f"No workflow found with ID {input.workflow_id}")

    # Group module calls and transformations by workflow
    workflow_data = {}
    for row in result.results:
        workflow_id = row["id"]
        if workflow_id not in workflow_data:
            workflow_data[workflow_id] = {
                "id": row["id"],
                "wf_id": row["wf_id"],
                "description": row["description"],
                "wffn": row["wffn"],
                "module_calls": {},
            }

        if row["mic_id"]:  # Only add if there's a module call
            if row["mic_id"] not in workflow_data[workflow_id]["module_calls"]:
                workflow_data[workflow_id]["module_calls"][row["mic_id"]] = {
                    "mic_id": row["mic_id"],
                    "modins": row["modins"],
                    "transformations": [],
                }

            if row["trafo_idx"]:  # Add transformation if it exists
                workflow_data[workflow_id]["module_calls"][row["mic_id"]][
                    "transformations"
                ].append(
                    {
                        "id": row["trafo_idx"],
                        "description": row["trafo_desc"],
                        "ord_nr": row["ord_nr"],
                    }
                )

    # Create markdown content
    markdown_content = f"""## Workflow: {workflow_data[input.workflow_id]["wf_id"]}
**Description:** {workflow_data[input.workflow_id]["description"]}

### Basic Information
| Property | Value |
|----------|--------|
| ID | {workflow_data[input.workflow_id]["id"]} |
| Function Name | {workflow_data[input.workflow_id]["wffn"]} |

"""

    # Add module calls and transformations if they exist
    if workflow_data[input.workflow_id]["module_calls"]:
        markdown_content += "### Module Calls and Their Transformations\n"
        for mic_id, module_call in workflow_data[input.workflow_id][
            "module_calls"
        ].items():
            markdown_content += f"\n#### Module: {module_call['modins']}\n"
            if module_call["transformations"]:
                markdown_content += (
                    "The following transformations are executed in this module:\n\n"
                )
                markdown_content += "| Order | Transformation ID | Description |\n"
                markdown_content += "|-------|------------------|-------------|\n"
                for trafo in sorted(
                    module_call["transformations"], key=lambda x: x["description"]
                ):
                    markdown_content += f"| {trafo['ord_nr']} | {trafo['id']} | {trafo['description']} |\n"
            else:
                markdown_content += "This module has no transformations.\n"
    else:
        markdown_content += "### Module Calls\nThis workflow has no module calls."

    # Add Mermaid diagram
    markdown_content += "\n### Workflow Structure\n```mermaid\ngraph TD\n"

    # Add workflow node
    markdown_content += (
        f"    WF[{workflow_data[input.workflow_id]['wf_id']}]:::workflow\n"
    )

    # Add module nodes and their connections
    if workflow_data[input.workflow_id]["module_calls"]:
        for mic_id, module_call in workflow_data[input.workflow_id][
            "module_calls"
        ].items():
            # Add module node
            markdown_content += f"    M{mic_id}[{module_call['modins']}]:::module\n"
            # Connect workflow to module
            markdown_content += f"    WF --> M{mic_id}\n"

            # Add transformation nodes if they exist
            if module_call["transformations"]:
                for trafo in sorted(
                    module_call["transformations"], key=lambda x: x["ord_nr"]
                ):
                    # Add transformation node
                    markdown_content += (
                        f"    T{trafo['id']}[{trafo['description']}]:::transformation\n"
                    )
                    # Connect module to transformation
                    markdown_content += f"    M{mic_id} --> T{trafo['id']}\n"

    # Add styles
    markdown_content += """
    classDef workflow fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef module fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef transformation fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
```\n"""

    # Convert module_calls dict to list for the output model
    module_calls_list = []
    for mic_id, module_call in workflow_data[input.workflow_id]["module_calls"].items():
        module_calls_list.append(
            {
                "mic_id": module_call["mic_id"],
                "modins": module_call["modins"],
                "ord_nr": 0,  # Default to 0 since we don't have module call order
            }
        )

    # Create the output using Pydantic models
    return WorkflowDetailsOutput(
        results=[
            WorkflowDetails(
                **{
                    **workflow_data[input.workflow_id],
                    "module_calls": module_calls_list,
                }
            )
        ],
        markdown_content=markdown_content,
    )
