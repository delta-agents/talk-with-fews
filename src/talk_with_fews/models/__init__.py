# Config
from talk_with_fews.models.timeseries_describe import (
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from talk_with_fews.models.timeseries_search import (
    TimeSeriesSearchInput,
    TimeSeriesSearchOutput,
)
from talk_with_fews.models.transformation_search import (
    TransformationSearchInput,
    TransformationSearchOutput,
)
from talk_with_fews.models.workflow_search import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
)
from talk_with_fews.models.workflow_details import (
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from talk_with_fews.models.workflow_hierarchy import WorkflowCallHierarchyInput
from talk_with_fews.models.dead_point_analysis import (
    DeadPointsAnalysisInput,
    DeadPointsAnalysisOutput,
)
from talk_with_fews.models.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.models.database_schema import (
    DatabaseSchemaOutput,
    DatabaseSchemaInput,
)
from talk_with_fews.models.graph import (
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from talk_with_fews.models.sql_query import SQLQueryInput, SQLQueryOutput

from talk_with_fews.models.transformation_details import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
)

# Webservice tools
# corresponding models
from talk_with_fews.models.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.models.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.models.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.models.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
)
from talk_with_fews.models.flags.io import (
    SeriesFlagsInput,
    SeriesFlagsOutput,
)
from talk_with_fews.models.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
)
from talk_with_fews.models.generate_xml_template import (
    XMLTemplateInput,
    XMLTemplateOutput,
)
from talk_with_fews.models.get_available_elements import (
    GetAvailableElementsInput,
    GetAvailableElementsOutput,
)

__all__ = [
    # config models
    "DescribeTimeSeriesInput",
    "DescribeTimeSeriesOutput",
    "TimeSeriesSearchInput",
    "TimeSeriesSearchOutput",
    "TransformationSearchInput",
    "TransformationSearchOutput",
    "TransformationDetailsOutput",
    "WorkflowSearchInput",
    "WorkflowSearchOutput",
    "WorkflowDetailsInput",
    "WorkflowDetailsOutput",
    "WorkflowCallHierarchyInput",
    "DeadPointsAnalysisInput",
    "DeadPointsAnalysisOutput",
    "DependencyAnalysisInput",
    "DependencyAnalysisOutput",
    "DatabaseSchemaInput",
    "DatabaseSchemaOutput",
    "GraphVisualizationInput",
    "GraphVisualizationOutput",
    "SQLQueryInput",
    "SQLQueryOutput",
    "TransformationDetailsInput",
    "TransformationDetailsOutput",
    # Webservice models
    "GetParameterInput",
    "GetParameterOutput",
    "GetLocationInput",
    "GetLocationOutput",
    "GetSeriesDataInput",
    "GetSeriesDataOutput",
    "GetSeriesHeadersInput",
    "GetSeriesHeadersOutput",
    "GetSeriesStatisticsInput",
    "GetSeriesStatisticsOutput",
    "SeriesFlagsInput",
    "SeriesFlagsOutput",
    "XMLValidationInput",
    "XMLValidationOutput",
    "XMLTemplateInput",
    "XMLTemplateOutput",
    "GetAvailableElementsInput",
    "GetAvailableElementsOutput",
]
