from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.base import Deps
from talk_with_fews.models.sql_query import SQLQueryInput

from talk_with_fews.models.transformation_details import (
    TransformationDetails,
    TransformationDetailsInput,
    TransformationDetailsOutput,
)
from talk_with_fews.tools.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def get_transformation_details(
    ctx: RunContext[Deps], input: TransformationDetailsInput
) -> TransformationDetailsOutput:
    """
    Get detailed information about a specific transformation, including its input and output time series.

    Args:
        ctx: RunContext with database connection
        input: TransformationDetailsInput containing the transformation ID

    Returns:
        TransformationDetailsOutput: A complete description of the transformation including:
            - Structured data about the transformation and its time series links
            - Pre-formatted markdown content for display
    """
    # Get transformation details and time series links
    query = f"""
    SELECT t.id, t.desc, t.ord_nr, t.config_file, t.mic_id, mc.modins,
           l.inout, ts.id as tss_id
    FROM trafos t
    JOIN modins_calls mc ON t.mic_id = mc.id
    LEFT JOIN links l ON t.id = l.trafo_id
    LEFT JOIN ts_sets ts ON l.tss_id = ts.id
    WHERE t.id = {input.transformation_id}
    ORDER BY l.inout, ts.id
    """

    result = await execute_query(ctx, SQLQueryInput(query=query))

    if not result.results:
        raise ModelRetry(f"No transformation found with ID {input.transformation_id}")

    # Group time series links by transformation
    transformation_data = {}
    for row in result.results:
        trafo_id = row["id"]
        if trafo_id not in transformation_data:
            transformation_data[trafo_id] = {
                "id": row["id"],
                "desc": row["desc"],
                "ord_nr": row["ord_nr"],
                "config_file": row["config_file"],
                "mic_id": row["mic_id"],
                "modins": row["modins"],
                "time_series_links": [],
            }

        if row["tss_id"]:  # Only add if there's a time series link
            transformation_data[trafo_id]["time_series_links"].append(
                {"inout": row["inout"], "tss_id": row["tss_id"]}
            )

    # Create markdown content
    markdown_content = f"""## Transformation Details
**ID:** {transformation_data[input.transformation_id]["id"]}
**Description:** {transformation_data[input.transformation_id]["desc"]}
**Config File:** {transformation_data[input.transformation_id]["config_file"]}

### Basic Information
| Property | Value |
|----------|--------|
| Order Number | {transformation_data[input.transformation_id]["ord_nr"]} |
| Module Instance | {transformation_data[input.transformation_id]["modins"]} |
| Module Config ID | {transformation_data[input.transformation_id]["mic_id"]} |

### Time Series Connections
This transformation processes the following time series:

#### Input Time Series
"""
    input_ts = [
        ts
        for ts in transformation_data[input.transformation_id]["time_series_links"]
        if ts["inout"] == "in"
    ]
    output_ts = [
        ts
        for ts in transformation_data[input.transformation_id]["time_series_links"]
        if ts["inout"] == "out"
    ]

    if input_ts:
        markdown_content += "| ID | Description |\n"
        markdown_content += "|----|-------------|\n"
        for ts in input_ts:
            markdown_content += f"| {ts['tss_id']} | Input time series |\n"
    else:
        markdown_content += "No input time series connected.\n"

    markdown_content += "\n#### Output Time Series\n"
    if output_ts:
        markdown_content += "| ID | Description |\n"
        markdown_content += "|----|-------------|\n"
        for ts in output_ts:
            markdown_content += f"| {ts['tss_id']} | Output time series |\n"
    else:
        markdown_content += "No output time series connected.\n"

    # Add Mermaid diagram
    markdown_content += "\n### Transformation Flow\n```mermaid\ngraph LR\n"

    # Add transformation node
    markdown_content += f"    T[{transformation_data[input.transformation_id]['desc']}]:::transformation\n"

    # Add input time series nodes and connections
    if input_ts:
        for ts in input_ts:
            markdown_content += (
                f"    I{ts['tss_id']}[Input TS {ts['tss_id']}]:::input\n"
            )
            markdown_content += f"    I{ts['tss_id']} --> T\n"

    # Add output time series nodes and connections
    if output_ts:
        for ts in output_ts:
            markdown_content += (
                f"    O{ts['tss_id']}[Output TS {ts['tss_id']}]:::output\n"
            )
            markdown_content += f"    T --> O{ts['tss_id']}\n"

    # Add styles
    markdown_content += """
    classDef transformation fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef input fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef output fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
```\n"""

    # Create the output using Pydantic models
    return TransformationDetailsOutput(
        results=[TransformationDetails(**transformation_data[input.transformation_id])],
        markdown_content=markdown_content,
    )
