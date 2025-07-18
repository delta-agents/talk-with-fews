from talk_with_fews.models.base import Location, Parameter
from talk_with_fews.utils.webservice_utils import get_request
import pandas as pd
import json


def get_locations(webservice_url, cache_FewsWebServices_db) -> None:
    """
    Retrieve ALL the locations from a web service and format the results.

    Args:
        webservice_url: URL of the FEWS web service
        cache_FewsWebServices_db: DuckDB connection for caching locations

    Returns:
        None
    """

    # check if webservice_url is set
    if webservice_url is None:
        raise ValueError(
            "Web service URL is not configured in the environment variables."
        )

    # Call the web service to get locations details
    request_url = f"{webservice_url}/rest/fewspiservice/v1/locations"

    document_format = "PI_JSON"  # can also be PI_XML, but we default to JSON for now
    params = dict(
        showAttributes="true",
        showParentLocations="true",
        showThresholds="true",
        includeIconNames="true",
        includeLocationRelations="true",
        includeTimeDependency="true",
        documentFormat=document_format,
    )

    error, data = get_request(request_url, params=params)
    data = json.loads(data) if isinstance(data, str) else data
    if error is not None:
        raise ValueError(f"Error fetching parameter details: {error}")

    # slightly inefficient, but due to the legacy code we leave it like this
    # doing it this way means the data is checked before being inserted
    locations = []
    # Process the response data to create TimeSeriesSearchOutput
    for value in data["locations"]:
        location = Location(
            locationId=value["locationId"],
            shortName=value["shortName"],
            lat=value["lat"],
            lon=value["lon"],
            x=value["x"],
            y=value["y"],
            z=value["z"],
            geoDatum=data["geoDatum"],  # in the main data, but still use full to have
            attributes=value["attributes"],
            relations=value["relations"],
        )
        locations.append(location)

    # Convert locations to DataFrame for easy DuckDB insertion
    locations_data = []
    for loc in locations:
        locations_data.append(
            {
                "locationId": loc.locationId,
                "shortName": loc.shortName,
                "lat": float(loc.lat) if loc.lat else None,
                "lon": float(loc.lon) if loc.lon else None,
                "x": float(loc.x) if loc.x else None,
                "y": float(loc.y) if loc.y else None,
                "z": float(loc.z) if loc.z else None,
                "geoDatum": loc.geoDatum,
                "attributes": json.dumps(loc.attributes) if loc.attributes else None,
                "relations": json.dumps(loc.relations)
                if hasattr(loc, "relations") and loc.relations
                else None,
            }
        )

    locations_df = pd.DataFrame(locations_data)

    # Create and populate the locations table in DuckDB
    cache_FewsWebServices_db.execute("DROP TABLE IF EXISTS locations")
    cache_FewsWebServices_db.execute("""
        CREATE TABLE locations (
            locationId VARCHAR,
            shortName VARCHAR,
            lat DOUBLE,
            lon DOUBLE,
            x DOUBLE,
            y DOUBLE,
            z DOUBLE,
            geoDatum VARCHAR,
            attributes VARCHAR,
            relations VARCHAR
        )
    """)

    # Insert data into DuckDB table
    locations_df  # so ruff doesn't complain
    cache_FewsWebServices_db.execute("INSERT INTO locations SELECT * FROM locations_df")

    # Verify data was inserted
    result = cache_FewsWebServices_db.execute(
        "SELECT COUNT(*) FROM locations"
    ).fetchone()
    assert result is not None, "Failed to insert locations into DuckDB table"


def get_parameters(webservice_url, cache_FewsWebServices_db) -> None:
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
            parameter_group_name=value["parameterGroupName"],
            short_name=value["shortName"],
            attributes=str(value["attributes"]),
        )
        parameters.append(parameter)

    # Convert locations to DataFrame for easy DuckDB insertion
    parameters_data = []
    for loc in parameters:
        parameters_data.append(
            {
                "id": loc.id,
                "name": loc.name,
                "parameter_type": loc.parameter_type,
                "unit": loc.unit,
                "display_unit": loc.display_unit,
                "uses_datum": loc.uses_datum,
                "parameter_group": loc.parameter_group,
                "parameter_group_name": loc.parameter_group_name,
                "short_name": loc.short_name,
                "attributes": json.dumps(loc.attributes) if loc.attributes else None,
            }
        )

    parameter_df = pd.DataFrame(parameters_data)

    # Create and populate the parameters table in DuckDB
    cache_FewsWebServices_db.execute("DROP TABLE IF EXISTS parameters")
    cache_FewsWebServices_db.execute("""
        CREATE TABLE parameters (
            id VARCHAR,
            name VARCHAR,
            parameter_type VARCHAR,
            unit VARCHAR,
            display_unit VARCHAR,
            uses_datum BOOLEAN,
            parameter_group VARCHAR,
            parameter_group_name VARCHAR,
            short_name VARCHAR,
            attributes VARCHAR
        )
    """)
    parameter_df # so ruff doesn't complain
    # Register the DataFrame as a DuckDB view    # Insert data into DuckDB table
    cache_FewsWebServices_db.execute("INSERT INTO parameters SELECT * FROM parameter_df")

    # Verify data was inserted
    result = cache_FewsWebServices_db.execute(
        "SELECT COUNT(*) FROM parameters"
    ).fetchone()
    assert result is not None, "Failed to insert parameters into DuckDB table"
