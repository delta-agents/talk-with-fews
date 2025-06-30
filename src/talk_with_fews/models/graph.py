"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Model representing a node in a graph visualization.

    A node represents an entity (time series, transformation, or workflow) in the graph.

    Attributes:
        id: Unique identifier of the entity
        type: Type of entity (timeseries, transformation, workflow)
        label: Display label for the node
        properties: Additional properties to display
        level: Optional level in the hierarchy (for hierarchical layouts)
    """

    id: int = Field(..., description="Unique identifier of the entity")
    type: str = Field(
        ..., description="Type of entity (timeseries, transformation, workflow)"
    )
    label: str = Field(..., description="Display label for the node")
    properties: Dict[str, str] = Field(
        default_factory=dict, description="Additional properties to display"
    )
    level: Optional[int] = Field(None, description="Optional level in the hierarchy")


class GraphEdge(BaseModel):
    """Model representing an edge in a graph visualization.

    An edge represents a relationship between entities in the graph.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        type: Type of relationship (e.g., 'input', 'output', 'calls')
        label: Optional label to display on the edge
        properties: Additional properties of the relationship
    """

    source_id: int = Field(..., description="ID of the source node")
    target_id: int = Field(..., description="ID of the target node")
    type: str = Field(..., description="Type of relationship")
    label: Optional[str] = Field(
        None, description="Optional label to display on the edge"
    )
    properties: Dict[str, str] = Field(
        default_factory=dict, description="Additional properties of the relationship"
    )


class GraphLayout(BaseModel):
    """Model defining how the graph should be laid out.

    This model specifies the visualization parameters for the graph.

    Attributes:
        layout_type: Type of layout to use (e.g., 'hierarchical', 'force-directed')
        direction: Direction for hierarchical layouts (e.g., 'LR', 'TB')
        max_depth: Maximum depth for hierarchical layouts
        node_spacing: Spacing between nodes
        level_spacing: Spacing between levels in hierarchical layouts
    """

    layout_type: str = Field("hierarchical", description="Type of layout to use")
    direction: str = Field("LR", description="Direction for hierarchical layouts")
    max_depth: Optional[int] = Field(
        None, description="Maximum depth for hierarchical layouts"
    )
    node_spacing: int = Field(50, description="Spacing between nodes")
    level_spacing: int = Field(100, description="Spacing between levels")


class GraphVisualizationInput(BaseModel):
    """Model for the input of graph visualization tools.

    This model defines the parameters for creating a graph visualization.

    Attributes:
        root_entity_type: Type of the root entity to visualize
        root_entity_id: ID of the root entity
        layout: Optional layout parameters
        include_properties: Whether to include detailed properties in the visualization
        max_nodes: Maximum number of nodes to include (for performance)
    """

    root_entity_type: str = Field(
        ..., description="Type of the root entity to visualize"
    )
    root_entity_id: int = Field(..., description="ID of the root entity")
    layout: Optional[GraphLayout] = Field(
        None, description="Optional layout parameters"
    )
    include_properties: bool = Field(
        False, description="Whether to include detailed properties"
    )
    max_nodes: Optional[int] = Field(
        None, description="Maximum number of nodes to include"
    )


class GraphVisualizationOutput(BaseModel):
    """Model for the output of graph visualization tools.

    This model provides the graph data needed for visualization.

    Attributes:
        nodes: List of nodes in the graph
        edges: List of edges in the graph
        layout: Layout parameters used
        markdown_content: Optional markdown representation of the graph
    """

    nodes: List[GraphNode] = Field(..., description="List of nodes in the graph")
    edges: List[GraphEdge] = Field(..., description="List of edges in the graph")
    layout: GraphLayout = Field(..., description="Layout parameters used")
    markdown_content: Optional[str] = Field(
        None, description="Optional markdown representation of the graph"
    )
