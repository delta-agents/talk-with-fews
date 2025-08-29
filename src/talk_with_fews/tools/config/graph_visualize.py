"""
Tools for the FEWS Configuration Agent.

This module defines the tools used by the agent to query and analyze FEWS configurations.
"""

from typing import Dict

from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.models.timeseries_describe import DescribeTimeSeriesInput
from talk_with_fews.models.transformation_details import TransformationDetailsInput
from talk_with_fews.models.workflow_details import WorkflowDetailsInput
from talk_with_fews.tools.config.timeseries_describe import describe_timeseries
from talk_with_fews.tools.config.transformation_details import (
    get_transformation_details,
)
from talk_with_fews.tools.config.workflows_details import get_workflow_details
from talk_with_fews.models.graph import (
    GraphEdge,
    GraphLayout,
    GraphNode,
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call


@log_tool_call
async def visualize_graph(
    ctx: RunContext[Deps], input: GraphVisualizationInput
) -> GraphVisualizationOutput:
    """Generate a graph visualization of FEWS entities and their relationships.

    This tool creates a graph visualization starting from a root entity (time series,
    transformation, or workflow) and shows its relationships with other entities.
    The output is formatted as a Mermaid diagram in markdown.

    Args:
        ctx: RunContext with database connection
        input: Visualization parameters including root entity and layout settings

    Returns:
        GraphVisualizationOutput containing nodes, edges, and Mermaid markdown
    """
    # Initialize layout parameters
    layout = input.layout or GraphLayout()
    max_depth = layout.max_depth or 3
    max_nodes = input.max_nodes or 50

    # Initialize lists to store nodes and edges
    nodes = []
    edges = []
    node_count = 0

    def add_node(
        entity_type: str,
        entity_id: int,
        label: str,
        properties: Dict[str, str] = None,
        level: int = 0,
    ) -> bool:
        """Helper function to add a node if we haven't exceeded limits."""
        nonlocal node_count
        if node_count >= max_nodes:
            return False

        node = GraphNode(
            id=entity_id,
            type=entity_type,
            label=label,
            properties=properties or {},
            level=level,
        )
        nodes.append(node)
        node_count += 1
        return True

    def add_edge(
        source_id: int,
        target_id: int,
        edge_type: str,
        label: str = None,
        properties: Dict[str, str] = None,
    ):
        """Helper function to add an edge."""
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            label=label,
            properties=properties or {},
        )
        edges.append(edge)

    async def get_time_series_node(tss_id: int, level: int = 0) -> bool:
        """Get time series node and its relationships using describe_timeseries tool."""
        # Get time series details
        time_series_result = await describe_timeseries(
            ctx, DescribeTimeSeriesInput(timeseries_id=tss_id)
        )
        if not time_series_result.results:
            return False

        time_series = time_series_result.results[0]

        # Create node label and properties
        label = time_series.description
        properties = {"type": time_series.tstype, "timestep": time_series.timess}

        # Add the node
        if not add_node("timeseries", time_series.id, label, properties, level):
            return False

        # Get transformations if we haven't reached max depth
        if level < max_depth and time_series.transformations:
            for trans in time_series.transformations:
                # Add transformation node
                trafo_label = f"{trans.module_config}|{trans.trafo_desc}"
                if add_node(
                    "transformation",
                    trans.trafo_id,
                    trafo_label,
                    {"order": str(trans.ord_nr)},
                    level + 1,
                ):
                    # Add edge from time series to transformation
                    add_edge(
                        tss_id, trans.trafo_id, "used_by", f"in {trans.module_config}"
                    )

                    # Get linked time series
                    if trans.linked_tss_modins:
                        linked_label = f"{trans.linked_tss_modins}|{trans.linked_tss_parid}|{trans.linked_tss_qualifiers}"
                        if add_node(
                            "timeseries", 0, linked_label, {}, level + 2
                        ):  # ID 0 for linked time series
                            add_edge(
                                trans.trafo_id,
                                0,
                                "produces",
                                f"out {trans.module_config}",
                            )

        return True

    async def get_transformation_node(trafo_id: int, level: int = 0) -> bool:
        """Get transformation node and its relationships using get_transformation_details tool."""
        # Get transformation details
        trafo_result = await get_transformation_details(
            ctx, TransformationDetailsInput(transformation_id=trafo_id)
        )
        if not trafo_result.results:
            return False

        trafo = trafo_result.results[0]

        # Create node label and properties
        label = f"{trafo.modins}|{trafo.desc}"
        properties = {"order": str(trafo.ord_nr)}

        # Add the node
        if not add_node("transformation", trafo.id, label, properties, level):
            return False

        # Get time series links if we haven't reached max depth
        if level < max_depth and trafo.time_series_links:
            for link in trafo.time_series_links:
                # Recursively get time series nodes
                if await get_time_series_node(link.tss_id, level + 1):
                    # Add appropriate edge based on direction
                    if link.inout == "in":
                        add_edge(
                            link.tss_id, trafo.id, "input_to", f"input {trafo.modins}"
                        )
                    else:
                        add_edge(
                            trafo.id, link.tss_id, "produces", f"output {trafo.modins}"
                        )

        return True

    async def get_workflow_node(workflow_id: int, level: int = 0) -> bool:
        """Get workflow node and its relationships using get_workflow_details tool."""
        # Get workflow details
        workflow_result = await get_workflow_details(
            ctx, WorkflowDetailsInput(workflow_id=workflow_id)
        )
        if not workflow_result.results:
            return False

        workflow = workflow_result.results[0]

        # Create node label and properties
        label = workflow.wf_id
        properties = {"description": workflow.desc}

        # Add the node
        if not add_node("workflow", workflow.id, label, properties, level):
            return False

        # Get module calls if we haven't reached max depth
        if level < max_depth and workflow.module_calls:
            for call in workflow.module_calls:
                # Recursively get transformation nodes
                if await get_transformation_node(call.mic_id, level + 1):
                    # Add edge from workflow to transformation
                    add_edge(workflow.id, call.mic_id, "contains", f"in {call.modins}")

        return True

    # Start building the graph from the root entity
    if input.root_entity_type == "timeseries":
        await get_time_series_node(input.root_entity_id)
    elif input.root_entity_type == "transformation":
        await get_transformation_node(input.root_entity_id)
    elif input.root_entity_type == "workflow":
        await get_workflow_node(input.root_entity_id)

    # Generate Mermaid diagram
    mermaid_lines = ["```mermaid", "graph " + layout.direction]

    # Add node definitions
    for node in nodes:
        # Create node label with properties if requested
        label = node.label
        if input.include_properties and node.properties:
            props = ", ".join(f"{k}: {v}" for k, v in node.properties.items())
            label = f"{label}<br/>({props})"

        # Add node with appropriate styling based on type
        style = {
            "timeseries": "fill:#e1f5fe,stroke:#01579b",
            "transformation": "fill:#f3e5f5,stroke:#4a148c",
            "workflow": "fill:#e8f5e9,stroke:#1b5e20",
        }.get(node.type, "")

        mermaid_lines.append(f'{node.id}["{label}"]:::{style}')

    # Add edge definitions
    for edge in edges:
        # Create edge label with properties if requested
        label = edge.label or ""
        if input.include_properties and edge.properties:
            props = ", ".join(f"{k}: {v}" for k, v in edge.properties.items())
            label = f"{label} ({props})"

        # Add edge with appropriate styling based on type
        style = {
            "used_by": "stroke:#01579b",
            "produces": "stroke:#1b5e20",
            "contains": "stroke:#4a148c",
            "input_to": "stroke:#01579b",
        }.get(edge.type, "")

        mermaid_lines.append(
            f"{edge.source_id} -->|{label}| {edge.target_id}:::{style}"
        )

    mermaid_lines.append("```")

    # Create markdown content
    markdown_content = "\n".join(mermaid_lines)

    return GraphVisualizationOutput(
        nodes=nodes, edges=edges, layout=layout, markdown_content=markdown_content
    )
