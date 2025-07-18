from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.base import Location


@log_tool_call
async def get_locations(
    ctx: RunContext[Deps], input: GetLocationInput
) -> GetLocationOutput:
    """
    Retrieve location details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: GetLocationInput containing request parameters
    Returns:
        GetLocationOutput: Retrieved locations details with formatted markdown content
    """

    # TODO adjust input to filter on parameters

    # Query locations from DuckDB
    query = "SELECT locationId, shortName, lat, lon, x, y, z, geoDatum FROM locations"
    connection = ctx.deps.cache_FewsWebServices_db
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
        markdown_content += (
            "| Location ID | Short Name | Latitude | Longitude | X | Y | Geo Datum |\n"
        )
        markdown_content += (
            "|-------------|------------|----------|-----------|---|---|----------|\n"
        )

        for location in locations:
            markdown_content += f"| {location.locationId} | {location.shortName} | {location.lat} | {location.lon} | {location.x} | {location.y} | {location.geoDatum} |\n"
    else:
        markdown_content += "No locations found matching the criteria.\n"

    return GetLocationOutput(
        locations=locations,
        markdown_content=markdown_content,
    )
