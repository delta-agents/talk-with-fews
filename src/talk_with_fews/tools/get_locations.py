import json
from pydantic_ai import RunContext

from talk_with_fews.models.base import Deps

from talk_with_fews.models.get_locations import (
    GetLocationInput,
    GetLocationOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call
from talk_with_fews.models.base import Location
from talk_with_fews.utils.webservice_utils import get_request


@log_tool_call
async def get_locations(
    ctx: RunContext[Deps], input: GetLocationInput
) -> GetLocationOutput:
    """
    Retrieve location details from a web service and format the results.

    Args:
        ctx: RunContext with database connection
        input: LocationDetailsInput containing request parameters
    Returns:
        LocationDetailsOutput: Retrieved parameter details with formatted markdown content
    """

    webservice_url = ctx.deps.webservice_url
    # check if webservice_url is set
    if webservice_url is None:
        raise ValueError(
            "Web service URL is not configured in the environment variables."
        )

    # Call the web service to get parameter details
    request_url = f"{webservice_url}/rest/fewspiservice/v1/locations"

    document_format = "PI_JSON"  # can also be PI_XML, but we default to JSON for now
    params = dict(
        showAttributes={str(input.show_attributes).lower()},
        showParentLocations={str(input.show_parent_locations).lower()},
        showThresholds={str(input.show_thresholds).lower()},
        includeIconNames={str(input.include_icon_names).lower()},
        includeLocationRelations={str(input.include_location_relations).lower()},
        includeTimeDependency={str(input.include_time_dependency).lower()},
        documentFormat=document_format,
    )
    if input.parameters is not None:
        parameter_ids = ""
        for parameter in input.parameters:
            parameter_ids += f"{str(parameter.id)},"
        params["parameterIds"] = parameter_ids

    if input.parameter_group is not None:
        group_ids = ""
        for parameter in input.parameter_group:
            group_ids += f"{str(parameter.parameter_group)},"
        params["parameterGroupId"] = group_ids

    error, data = get_request(request_url, params=params)
    data = json.loads(data) if isinstance(data, str) else data
    if error is not None:
        raise ValueError(f"Error fetching parameter details: {error}")

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
            attributes=value["attributes"] if input.show_attributes else None,
            relations=value["relations"] if input.include_location_relations else None,
        )
        locations.append(location)

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
