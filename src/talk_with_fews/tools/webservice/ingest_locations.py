from talk_with_fews.models.base import Location
from talk_with_fews.models.ingest_webservice import IngestLocationsOutput
from talk_with_fews.utils.webservice_utils import get_request
from talk_with_fews.utils.logging_utils import logger

import pandas as pd
import json
import duckdb
import geopandas as gpd


def ingest_locations(
    webservice_url, cache_FewsWebServices_db: duckdb.DuckDBPyConnection
) -> IngestLocationsOutput:
    """
    Retrieve ALL the locations from a web service and format the results and store in local data store.

    Args:
        webservice_url: URL of the FEWS web service
        cache_FewsWebServices_db: DuckDB connection for caching locations

    Returns:
        None
    """

    # check if webservice_url is set
    if webservice_url is None:
        logger.error("Web service URL is not configured in the environment variables.")
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
    if error == "only contains is supported":  # error seen for WSBD
        params["showThresholds"] = "false"
        error, data = get_request(request_url, params=params)
        logger.debug("Set `include_thresholds` to false")

    if error is not None:
        logger.error(f"Error fetching locations details: {error}")
        raise ValueError(f"Error fetching parameter details: {error}")

    # slightly inefficient, but due to the legacy code we leave it like this
    # doing it this way means the data is checked before being inserted
    data = json.loads(data) if isinstance(data, str) else data
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
            description=value.get("description"),
            parentLocationId=value.get("parentLocationId"),
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
                "description": loc.description,
                "parentLocationId": loc.parentLocationId,
                "attributes": json.dumps(loc.attributes) if loc.attributes else None,
                "relations": json.dumps(loc.relations)
                if hasattr(loc, "relations") and loc.relations
                else None,
            }
        )

    locations_df = pd.DataFrame(locations_data)
    locations_df["lon"] = locations_df["lon"].fillna(0)
    locations_df["lat"] = locations_df["lat"].fillna(0)
    locations_gdf = gpd.GeoDataFrame(
        locations_df,
        geometry=gpd.points_from_xy(locations_df.lon, locations_df.lat),
        crs="EPSG:4326",  # Assuming WGS84 for lat/lon
    )
    locations_gdf["geom"] = locations_gdf["geometry"].to_wkt()
    locations_gdf.drop(columns="geometry", inplace=True)
    locations_gdf["series_headers_retrieved"] = False

    # Create and populate the locations table in DuckDB
    cache_FewsWebServices_db.execute("DROP TABLE IF EXISTS locations")
    cache_FewsWebServices_db.execute("""
        CREATE TABLE locations (
            locationId VARCHAR PRIMARY KEY,
            shortName VARCHAR,
            lat DOUBLE,
            lon DOUBLE,
            x DOUBLE,
            y DOUBLE,
            z DOUBLE,
            geoDatum VARCHAR,
            description VARCHAR,
            parentLocationId VARCHAR,
            attributes VARCHAR,
            relations VARCHAR,
            geom GEOMETRY, -- Add geometry column for spatial data
            series_headers_retrieved BOOLEAN DEFAULT FALSE -- Column to track if series headers have been ingested
        )
    """)
    logger.info(f"Ingesting {len(locations_gdf)} locations into DuckDB")
    # logger.info(f"Ingesting {len(locations_gdf.columns)} columns into DuckDB")
    # locations_gdf.to_file("locations_gdf.csv")

    # Insert data into DuckDB table
    cache_FewsWebServices_db.execute(
        "INSERT INTO locations SELECT * FROM locations_gdf"
    )
    del locations_gdf

    # TODO: add a view for the locations table
    cache_FewsWebServices_db.execute("""
        CREATE OR REPLACE VIEW locations_view AS
        SELECT
            locationId,
            shortName,
            geom
        FROM locations
        WHERE lat IS NOT NULL AND lon IS NOT NULL
        ORDER BY shortName
    """)

    # Verify data was inserted
    result = cache_FewsWebServices_db.execute(
        "SELECT COUNT(*) FROM locations"
    ).fetchone()
    assert result is not None, "Failed to insert locations into DuckDB table"

    return IngestLocationsOutput(
        description="Locations ingested successfully",
        sql_examples=[
            "SELECT * FROM locations_view WHERE ST_Within(geom, ST_GeomFromText('POLYGON((4.8 52.3, 4.9 52.3, 4.9 52.4, 4.8 52.4, 4.8 52.3))'))",
            "SELECT * FROM locations_view WHERE ST_DWithin(geom, ST_Point(4.85, 52.35), 0.01)",
            "SELECT locationId, shortName, ST_AsText(geom) FROM locations_view LIMIT 10",
            "SELECT * FROM locations_view",
        ],
    )
