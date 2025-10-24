# Config
from talk_with_fews.models.config.timeseries_describe import (
    DescribeTimeSeriesInput,
    DescribeTimeSeriesOutput,
)
from talk_with_fews.models.config.timeseries_search import (
    TimeSeriesSearchInput,
    TimeSeriesSearchOutput,
)
from talk_with_fews.models.config.transformation_search import (
    TransformationSearchInput,
    TransformationSearchOutput,
)
from talk_with_fews.models.config.workflow_search import (
    WorkflowSearchInput,
    WorkflowSearchOutput,
)
from talk_with_fews.models.config.workflow_details import (
    WorkflowDetailsInput,
    WorkflowDetailsOutput,
)
from talk_with_fews.models.config.workflow_hierarchy import WorkflowCallHierarchyInput
from talk_with_fews.models.config.dead_point_analysis import (
    DeadPointsAnalysisInput,
    DeadPointsAnalysisOutput,
)
from talk_with_fews.models.config.dependency_analysis import (
    DependencyAnalysisInput,
    DependencyAnalysisOutput,
)
from talk_with_fews.models.config.database_schema import (
    DatabaseSchemaOutput,
    DatabaseSchemaInput,
)
from talk_with_fews.models.config.graph import (
    GraphVisualizationInput,
    GraphVisualizationOutput,
)
from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput

from talk_with_fews.models.config.transformation_details import (
    TransformationDetailsInput,
    TransformationDetailsOutput,
)

# Webservice tools
# corresponding models
from talk_with_fews.models.webservice.get_webservice_info import (
    GetWebServiceInfoInput,
    GetWebServiceInfoOutput,
)
from talk_with_fews.models.webservice.get_parameters import (
    GetParameterInput,
    GetParameterOutput,
)
from talk_with_fews.models.webservice.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.models.webservice.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.models.webservice.get_series_statistics import (
    GetSeriesStatisticsInput,
    GetSeriesStatisticsOutput,
)
from talk_with_fews.models.webservice.get_series_data import (
    GetSeriesDataInput,
    GetSeriesDataOutput,
)
from talk_with_fews.models.webservice.flags.io import (
    SeriesFlagsInput,
    SeriesFlagsOutput,
)

# XML
from talk_with_fews.models.validator.validate_xml import (
    XMLValidationInput,
    XMLValidationOutput,
)
from talk_with_fews.models.validator.generate_xml_template import (
    XMLTemplateInput,
    XMLTemplateOutput,
)
from talk_with_fews.models.validator.get_available_elements import (
    GetAvailableElementsInput,
    GetAvailableElementsOutput,
)
from talk_with_fews.models.validator.fews_schema_options import FEWSSchemaOption

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
    "GetWebServiceInfoInput",
    "GetWebServiceInfoOutput",
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
    # XML models
    "XMLValidationInput",
    "XMLValidationOutput",
    "XMLTemplateInput",
    "XMLTemplateOutput",
    "GetAvailableElementsInput",
    "GetAvailableElementsOutput",
    "FEWSSchemaOption",
]
