import sqlite3
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import duckdb

from talk_with_fews.models.ingest_webservice import (
    IngestLocationsOutput,
    IngestParameterOutput,
)


class Transformation(BaseModel):
    """Model representing a transformation in the FEWS configuration.

    A transformation is a process that converts input time series into output time series
    according to specific rules defined in a module configuration.
    """

    trafo_id: int = Field(..., description="Unique identifier of the transformation")
    trafo_desc: str = Field(
        ..., description="Description of what the transformation does"
    )
    ord_nr: int = Field(
        ...,
        description="Order number indicating the sequence in the module configuration",
    )
    module_config_id: int = Field(
        ..., description="Unique identifier of the module configuration"
    )
    module_config: str = Field(
        ..., description="Name of the module instance containing this transformation"
    )
    workflow_id: int = Field(..., description="Unique identifier of the workflow")
    workflow_name: str = Field(..., description="Name of the workflow")
    workflow_desc: str = Field(..., description="Description of the workflow")
    inout: str = Field(
        ...,
        description="Indicates if the time series is used as input ('in') or output ('out')",
    )
    linked_tss_modins: Optional[str] = Field(
        None, description="Module instance of the linked time series"
    )
    linked_tss_parid: Optional[str] = Field(
        None, description="Parameter ID of the linked time series"
    )
    linked_tss_qualifiers: Optional[str] = Field(
        None, description="Qualifiers of the linked time series"
    )


class Parameter(BaseModel):
    """Model representing a parameter in the FEWS configuration.

    A parameter is a specific variable or characteristic that can be measured or calculated
    within the FEWS system, such as soil moisture or water level.
    """

    id: str = Field(..., description="Unique identifier of the parameter")
    name: str = Field(..., description="Name of the parameter")
    parameter_type: str = Field(..., description="Type of parameter")
    unit: str = Field(..., description="Unit of measurement for the parameter")
    display_unit: str = Field(..., description="Unit used for display purposes")
    uses_datum: bool = Field(..., description="Whether the parameter uses datum")
    parameter_group: str = Field(
        ..., description="Parameter group to which this parameter belongs"
    )
    parameter_group_name: str = Field(..., description="Parameter group name")
    short_name: str = Field(..., description="Short name of the parameter")
    attributes: str | None = Field(
        None, description="Stringified JSON of additional attributes for the parameter"
    )


class Location(BaseModel):
    """Model representing a location in the FEWS configuration.

    A location is a point or area where measurements are taken or where parameters are defined
    within the FEWS system, such as a weather station or a river gauge.
    """

    locationId: str = Field(..., description="Unique identifier of the location")
    shortName: str = Field(..., description="Short name of the location")
    lat: float = Field(..., description="Latitude coordinate")
    lon: float = Field(..., description="Longitude coordinate")
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    z: float | None = Field(..., description="Z coordinate (elevation)")
    geoDatum: str = Field(
        ..., description="Geographic datum used for the location coordinates"
    )
    attributes: Optional[List[Dict[str, Any]]] | None = Field(
        None, description="List of location attributes"
    )


class ModuleInstanceCall(BaseModel):
    """Model representing a module instance call within a workflow.

    A module instance call represents the execution of a specific module configuration
    within a workflow, including its order and description.
    """

    mic_id: int = Field(
        ..., description="Unique identifier of the module instance call"
    )
    modins: str = Field(..., description="Name of the module instance being called")
    ord_nr: int = Field(
        ..., description="Order number indicating the sequence in the workflow"
    )


class TimeSeriesLink(BaseModel):
    """Model representing a time series linked to a transformation.

    A time series link represents how a time series is connected to a transformation,
    either as input or output. The time series properties can be retrieved using the tss_id.
    """

    inout: str = Field(
        ...,
        description="Indicates if the time series is used as input ('in') or output ('out')",
    )
    tss_id: int = Field(..., description="Unique identifier of the time series")


class TimeSeriesProperties(BaseModel):
    """Model representing the core properties of a time series in the FEWS configuration.

    A time series is a sequence of data points indexed in time order. In FEWS, each time series
    has specific properties that define its characteristics and how it's used in the system.
    """

    id: int = Field(..., description="Unique identifier of the time series")
    modins: str = Field(
        ..., description="Module instance that owns or manages this time series"
    )
    vtype: str = Field(
        ..., description="Value type of the time series (e.g., 'scalar', 'vector')"
    )
    parid: str = Field(
        ..., description="Parameter identifier (e.g., 'bodemvocht_e' for soil moisture)"
    )
    qualifiers: str = Field(
        ...,
        description="Additional qualifiers that specify the time series (e.g., '30cm_minmv' for 30cm minimum value)",
    )
    tstype: str = Field(
        ..., description="Type of time series (e.g., 'external historical', 'internal')"
    )
    timess: str = Field(
        ..., description="Time step of the time series (e.g., '10minute', '1hour')"
    )
    description: str = Field(
        ...,
        description="Formatted string describing the time series using the standard template",
    )
    endpoint: bool = Field(False, description="Whether this time series is an endpoint")
    endpoint_desc: Optional[str] = Field(
        None, description="Endpoint description if the time series is an endpoint"
    )
    transformations: Optional[List[Transformation]] = Field(
        None,
        description="Optional list of transformations that use this time series as input or output",
    )


class AgentResponse(BaseModel):
    """
    Model for standardized agent responses.

    This model provides a consistent structure for all agent responses,
    allowing for text, tables, and diagram content.

    Attributes:
        markdown_text: Primary text response in markdown format
        markdown_table: Optional tabular data in markdown format
        mermaid_diagram: Optional mermaid diagram code
    """

    markdown_text: str = Field(
        ..., description="Primary text response in markdown format"
    )
    markdown_table: Optional[str] = Field(
        None, description="Optional tabular data in markdown format"
    )
    mermaid_diagram: Optional[str] = Field(
        None,
        description="Optional mermaid diagram code, makee sure it uses nodes on a new line",
    )


class ModuleSummary(BaseModel):
    """Model representing a summary of dead points by module."""

    module: str = Field(..., description="Module instance name")
    count: int = Field(..., description="Number of dead points in this module")


class ToolCallTracker:
    """Class to track tool calls and their results.

    This class is used to maintain a history of tool calls and their outcomes,
    which can be useful for debugging and analysis.
    """

    def __init__(self):
        self.calls = []


class Deps:
    """
    Dependencies for the FEWS Configuration Agent.

    Attributes:
        db_connection: SQLite database connection
        db_path: Path to the SQLite database
        schema: Comprehensive database schema information
        tracker: Tool call tracker
        webservice_url: Optional URL for the web service if applicable
    """

    def __init__(
        self,
        db_path: str = None,
        db_connection: sqlite3.Connection = None,
        tracker: ToolCallTracker = None,
    ):
        self.db_path = db_path
        self.db_connection = db_connection
        self.tracker = tracker
        self.schema: Optional[Dict[str, Any]] = None
        self.webservice_url: Optional[str] = None
        self.cache_FewsWebServices_db: Optional[duckdb.DuckDBPyConnection] = None
        self.ingest_locations_output: Optional[IngestLocationsOutput] = None
        self.ingest_parameters_output: Optional[IngestParameterOutput] = None
