from pydantic_ai import RunContext

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
                - filter_locations_name: An optional filter to search locations by their locationId, shortName, or description
    Returns:
        GetLocationOutput: Retrieved locations details with formatted markdown content
    """
    if input.number_of_locations is not None:
        n = input.number_of_locations
    else:
        n = 10

    columns = "locationId, shortName, lat, lon, x, y, z, geoDatum, description, parentLocationId"
    # Query locations from DuckDB
    if input.filter_locations_name is not None:
        # Search locationId, shortName, and description for the filter term
        query = f"SELECT {columns} FROM locations WHERE locationId ILIKE '%{input.filter_locations_name}%' OR shortName ILIKE '%{input.filter_locations_name}%' OR description ILIKE '%{input.filter_locations_name}%'"
    else:
        query = f"SELECT {columns} FROM locations"
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
                        "description",
                        "parentLocationId",
                    ],
                    row,
                )
            )
        )
        for row in rows
    ]

    # Generate brief, clear summary
    if not locations:
        if input.filter_locations_name:
            description = f"No locations found matching '{input.filter_locations_name}'"
        else:
            description = "No locations available"
    else:
        count = len(locations)

        # Analyze the results to provide clear summary
        child_locations = [loc for loc in locations if loc.parentLocationId is not None]

        if count == 1:
            loc = locations[0]
            if loc.parentLocationId:
                description = f"Found 1 location: '{loc.shortName}' (child of '{loc.parentLocationId}')"
            else:
                description = f"Found 1 location: '{loc.shortName}'"
        elif count <= 5:
            # For small results, mention key details
            if child_locations:
                description = (
                    f"Found {count} locations: {len(child_locations)} child locations"
                )
            else:
                location_names = [loc.shortName for loc in locations[:3]]
                if count > 3:
                    location_names.append(f"and {count - 3} more")
                description = f"Found {count} locations: {', '.join(location_names)}"
        else:
            # For larger results, provide summary
            if child_locations:
                description = (
                    f"Found {count} locations: {len(child_locations)} child locations"
                )
            else:
                description = f"Found {count} locations"

    return GetLocationOutput(
        locations=locations,
        description=description,
    )
