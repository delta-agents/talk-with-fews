from talk_with_fews.models.base import Parameter
from talk_with_fews.models.webservice.ingest_webservice import IngestParameterOutput
from talk_with_fews.utils.webservice_utils import get_request

import pandas as pd
import json
import duckdb


def ingest_parameters(
    webservice_url, cache_FewsWebServices_db: duckdb.DuckDBPyConnection
) -> IngestParameterOutput:
    """
    Retrieve ALL the parameters from a web service and format the results.

    Args:
        webservice_url: URL of the FEWS web service
        cache_FewsWebServices_db: DuckDB connection for caching locations
    Returns:
        None
    """

    documentFormat = "PI_JSON"  # can also be PI_XML, but we default to JSON for now

    # Call the web service to get parameter details
    request_url = f"{webservice_url}/rest/fewspiservice/v1/parameters"
    params = dict(showAttributes="true", documentFormat=documentFormat)
    error, data = get_request(request_url, params=params)
    data = json.loads(data) if isinstance(data, str) else data
    if error is not None:
        raise ValueError(f"Error fetching parameter details: {error}")

    parameters = []
    # Process the response data to create TimeSeriesSearchOutput
    for value in data["timeSeriesParameters"]:
        parameter = Parameter(
            id=value["id"],
            name=value["name"],
            parameter_type=value["parameterType"],
            unit=value["unit"],
            display_unit=value["displayUnit"],
            uses_datum=value["usesDatum"],
            parameter_group=value["parameterGroup"],
            short_name=value["shortName"],
            attributes=str(value["attributes"]),
        )
        parameters.append(parameter)

    # Convert parameters to DataFrame for easy DuckDB insertion
    parameters_data = []
    for param in parameters:
        parameters_data.append(
            {
                "id": param.id,
                "name": param.name,
                "parameter_type": param.parameter_type,
                "unit": param.unit,
                "display_unit": param.display_unit,
                "uses_datum": param.uses_datum,
                "parameter_group": param.parameter_group,
                "short_name": param.short_name,
                "attributes": json.dumps(param.attributes)
                if param.attributes
                else None,
            }
        )

    parameter_df = pd.DataFrame(parameters_data)
    parameter_df["series_headers_retrieved"] = False

    # Create and populate the parameters table in DuckDB
    cache_FewsWebServices_db.execute("DROP TABLE IF EXISTS parameters")
    cache_FewsWebServices_db.execute("""
        CREATE TABLE parameters (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            parameter_type VARCHAR,
            unit VARCHAR,
            display_unit VARCHAR,
            uses_datum BOOLEAN,
            parameter_group VARCHAR,
            short_name VARCHAR,
            attributes VARCHAR,
            -- New column to track if series headers have been ingested
            series_headers_retrieved BOOLEAN DEFAULT FALSE

        )
    """)
    # Insert data from the DataFrame into the DuckDB table
    cache_FewsWebServices_db.execute(
        "INSERT INTO parameters SELECT * FROM parameter_df"
    )
    del parameter_df

    # Verify data was inserted
    result = cache_FewsWebServices_db.execute(
        "SELECT COUNT(*) FROM parameters"
    ).fetchone()
    assert result is not None, "Failed to insert parameters into DuckDB table"

    parameter_count = result[0]

    # Return the ingestion output
    return IngestParameterOutput(
        description=f"Successfully ingested {parameter_count} parameters from {webservice_url}",
        sql_examples=[
            "SELECT * FROM parameters LIMIT 10;",
            "SELECT COUNT(*) FROM parameters;",
            "SELECT parameter_type, COUNT(*) FROM parameters GROUP BY parameter_type;",
            "SELECT * FROM parameters WHERE parameter_group = 'Water Level';",
        ],
    )
