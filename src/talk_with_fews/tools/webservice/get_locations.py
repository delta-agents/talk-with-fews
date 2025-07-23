from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.base import Location
import duckdb


@log_tool_call
async def get_locations(
    ctx: RunContext[Deps], input: GetLocationInput
) -> GetLocationOutput:
    """
    Retrieve a given number of location details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: GetLocationInput containing request parameters

               which includes:

                - number_of_locations: The maximum number of locations to retrieve
                - query: An optional search string to filter locations by specific criteria
                - locations_name: An optional name to filter locations by their name
    Returns:
        GetLocationOutput: Retrieved locations details with formatted markdown content
    """
    if input.number_of_locations is not None:
        n = input.number_of_locations
    else:
        n = 10

    # Query locations from DuckDB
    if input.query is not None:
        query = input.query
        try:
            assert "SELECT" in query, "Query must start with SELECT"
            assert any(
                col in query
                for col in [
                    "locationId",
                    "shortName",
                    "lat",
                    "lon",
                    "x",
                    "y",
                    "z",
                    "geoDatum",
                ]
            ), (
                "Query must include atleast one columns ocationId, shortName, lat, lon, x, y, z, geoDatum"
            )
            assert "FROM locations" in query, "Query must specify a table with FROM"
        except AssertionError as e:
            raise ModelRetry(f"Query validation failed: {str(e)}")
    else:
        query = (
            "SELECT locationId, shortName, lat, lon, x, y, z, geoDatum FROM locations"
        )
    if "LIMIT" not in query:
        query += f" LIMIT {n}"

    connection: duckdb.DuckDBPyConnection = ctx.deps.cache_FewsWebServices_db
    cursor = connection.cursor()
    data = cursor.execute(query)
    rows = data.fetchall()

    # Convert rows to Location objects
    locations = [
        Location(
            **dict(
                zip(
                    [
                        "locationId",
                        "shortName",
                        "lat",
                        "lon",
                        "x",
                        "y",
                        "z",
                        "geoDatum",
                    ],
                    row,
                )
            )
        )
        for row in rows
    ]

    # make a summary of the locations

    # TODO change this to make a summary of the parameters
    # Generate markdown content
    markdown_content = "## Locations\n\n"
    markdown_content += f"Found {len(locations)} locations.\n\n"

    if locations:
        markdown_content += "| Location ID | Short Name | Latitude | Longitude | X | Y | Geo Datum | geom |\n"
        markdown_content += "|-------------|------------|----------|-----------|---|---|----------| ---- |\n"

        for location in locations:
            markdown_content += f"| {location.locationId} | {location.shortName} | {location.lat} | {location.lon} | {location.x} | {location.y} | {location.geoDatum} |\n"
    else:
        markdown_content += "No locations found matching the criteria.\n"

    return GetLocationOutput(
        locations=locations,
        markdown_content=markdown_content,
        description=f"Retrieved {n} locations from the FEWS web service, for more information query using the tool ",
    )
