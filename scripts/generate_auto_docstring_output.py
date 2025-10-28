#!/usr/bin/env python3
"""
Generate markdown showing what @auto_docstring ACTUALLY generates.

This script shows the real output of the @auto_docstring decorator.
"""

import sys

sys.path.append("src")

from datetime import datetime
from talk_with_fews.utils.docstring_generator import auto_docstring


def get_auto_docstring_output():
    """Get what @auto_docstring actually generates."""

    # Import the models
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
    from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput
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

    # Create functions with @auto_docstring decorator using the EXACT descriptions from the router
    @auto_docstring(
        "Call this at the start of the conversation to return information about the configured FEWS webservice for the given user."
    )
    async def get_webservice_info(
        input: GetWebServiceInfoInput,
    ) -> GetWebServiceInfoOutput:
        pass

    @auto_docstring(
        "Get information about parameters. This is how to access parameters data."
        "By default 10 parameters are returned. "
        "If no query is provided, the first number parameters asked for are returned."
        "If a query is provided, the parameters are filtered by the query string."
    )
    async def get_parameters(input: GetParameterInput) -> GetParameterOutput:
        pass

    @auto_docstring(
        "Get location information from the FEWS WebService database. "
        "Returns location metadata including coordinates, names, and spatial geometry data. "
        "By default returns 10 locations. "
        "Features: "
        "- Filter locations using query string matching on location names/IDs "
        "- Access spatial geometry data in 'geom' field (EPSG:4326 coordinate system) "
        "- Control result size with limit parameter "
        "- Essential for identifying monitoring sites and their geographic properties"
    )
    async def get_locations(input: GetLocationInput) -> GetLocationOutput:
        pass

    @auto_docstring(
        """Execute SQL queries against the cached FEWS webservice database (DuckDB).

    This tool queries the webservice cache containing:
    - series_headers: Available time series combinations
    - locations: FEWS location data
    - parameters: FEWS parameter data

    Note: This queries the DuckDB cache, not the SQLite config database.

    SPATIAL ANALYSIS - CRITICAL COORDINATE SYSTEM INFORMATION:

    WARNING: The geom column is stored in EPSG:4326 (WGS84) coordinates (degrees).
    For accurate spatial analysis with distance calculations, buffers, and spatial joins,
    you MUST transform coordinates to EPSG:28992 (Dutch RD system) which uses meters.

    CORRECT spatial analysis pattern:
    ```sql
    -- Transform to Dutch coordinate system for accurate distance calculations
    SELECT
        locationId,
        shortName,
        ST_Distance(
            ST_Transform(geom, 'EPSG:4326', 'EPSG:28992'),  -- Transform to EPSG:28992 (meters)
            ST_Transform(ST_Point(5.6667, 52.0333), 'EPSG:4326', 'EPSG:28992')  -- Transform point to EPSG:28992
        ) as distance_meters
    FROM locations
    WHERE ST_DWithin(
        ST_Transform(geom, 'EPSG:4326', 'EPSG:28992'),  -- Transform to EPSG:28992
        ST_Transform(ST_Point(5.6667, 52.0333), 'EPSG:4326', 'EPSG:28992'),  -- Transform point to EPSG:28992
        1000  -- 1000 meters buffer
    )
    ```

    INCORRECT (will give results in degrees, not meters):
    ```sql
    SELECT ST_Distance(geom, ST_Point(5.6667, 52.0333)) FROM locations  -- WRONG!
    ```

    Coordinate Systems:
    - EPSG:4326 (WGS84): Stored geometry - degrees (lat/lon)
    - EPSG:28992 (Dutch RD): Use for spatial analysis - meters

    Spatial Functions: All ST_* functions work, but use ST_Transform(geom, 'EPSG:4326', 'EPSG:28992') for analysis.
    To return geometry data: use ST_AsText(geom) for WGS84 or ST_AsText(ST_Transform(geom, 'EPSG:4326', 'EPSG:28992')) for RD."""
    )
    async def query_webservice_cache(input: SQLQueryInput) -> SQLQueryOutput:
        pass

    @auto_docstring(
        "Get series headers from the FEWS WebService with incremental caching. "
        "Retrieves available time series metadata using an efficient caching strategy. "
        "Features include: "
        "- Query by parameter ID or location ID "
        "- Incremental caching (only fetch when needed) "
        "- Minimal but meaningful output for cost optimization "
        "- User-friendly follow-up suggestions "
        "- Automatic foreign key validation with existing data "
        "- Essential for discovering available time series and their properties"
    )
    async def get_series_headers(
        input: GetSeriesHeadersInput,
    ) -> GetSeriesHeadersOutput:
        pass

    @auto_docstring(
        "Get statistical summaries for time series from the FEWS WebService. "
        "Retrieves statistics such as mean, min, max, and count for specified series. "
        "Features include: "
        "- Must Query by parameter ID AND location ID, make sure the combination exists using get_series_headers first."
        "- Optionally Specify time range for statistics, else defaults 2 days"
        "- Useful for quick data exploration and validation "
        "- Returns summary statistics for each matching series"
    )
    async def get_series_statistics(
        input: GetSeriesStatisticsInput,
    ) -> GetSeriesStatisticsOutput:
        pass

    @auto_docstring(
        "Get timeseries data for a specific location-parameter combination. "
        "Must query by parameter ID AND location ID, make sure the combination exists using get_series_headers first."
        "Features include: "
        "- Query by location ID and parameter ID "
    )
    async def get_series_data(input: GetSeriesDataInput) -> GetSeriesDataOutput:
        pass

    @auto_docstring(
        "Analyze FEWS quality flags for a specific location-parameter combination. "
        "This tool analyzes existing quality flags in the timeseries. "
        "Features include: "
        "- Detailed flag distribution (counts and percentages) "
        "- Quality level summary (Reliable/Doubtful/Unreliable) "
        "- Origin tracking (Original/Corrected/Completed) "
        "- Complete flag descriptions and metadata "
        "Requirements: "
        "- Must provide location ID and parameter ID "
        "- Time range cannot be in the future "
        "- Start time must be before end time "
        "Example Use Cases: "
        "- Monitor data quality across different periods "
        "- Compare quality between locations/parameters "
        "- Identify problematic data sources"
    )
    async def analyze_series_flags(input: SeriesFlagsInput) -> SeriesFlagsOutput:
        pass

    tools = [
        {
            "name": "get_webservice_info",
            "endpoint": "/tools.webservice/get_webservice_info",
            "function": get_webservice_info,
        },
        {
            "name": "get_parameters",
            "endpoint": "/tools.webservice/get_parameters",
            "function": get_parameters,
        },
        {
            "name": "get_locations",
            "endpoint": "/tools.webservice/get_locations",
            "function": get_locations,
        },
        {
            "name": "query_webservice_cache",
            "endpoint": "/tools.webservice/query_webservice_cache",
            "function": query_webservice_cache,
        },
        {
            "name": "get_series_headers",
            "endpoint": "/tools.webservice/get_series_headers",
            "function": get_series_headers,
        },
        {
            "name": "get_series_statistics",
            "endpoint": "/tools.webservice/get_series_statistics",
            "function": get_series_statistics,
        },
        {
            "name": "get_series_data",
            "endpoint": "/tools.webservice/get_series_data",
            "function": get_series_data,
        },
        {
            "name": "analyze_series_flags",
            "endpoint": "/tools.webservice/analyze_series_flags",
            "function": analyze_series_flags,
        },
    ]

    return tools


def generate_markdown_documentation(tools: list) -> str:
    """Generate markdown documentation showing what @auto_docstring actually generates."""

    md_content = []

    # Header
    md_content.append("# MCP Tools - @auto_docstring ACTUAL Output")
    md_content.append("")
    md_content.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_content.append("")
    md_content.append(
        "This document shows the **actual output** of the `@auto_docstring` decorator."
    )
    md_content.append(
        "These are the docstrings that the decorator generates when applied to MCP tools."
    )
    md_content.append("")

    # Table of contents
    md_content.append("## Table of Contents")
    md_content.append("")
    for i, tool in enumerate(tools, 1):
        anchor = tool["name"].lower().replace("_", "-")
        md_content.append(f"{i}. [{tool['name']}](#{anchor})")
    md_content.append("")

    # Tool documentation
    for i, tool in enumerate(tools, 1):
        md_content.append(f"## {i}. {tool['name']}")
        md_content.append("")

        # Endpoint
        md_content.append(f"**Endpoint:** `{tool['endpoint']}`")
        md_content.append("")

        # Actual @auto_docstring output
        md_content.append("**@auto_docstring Generated Docstring:**")
        md_content.append("")
        md_content.append("```python")
        if tool["function"].__doc__:
            md_content.append(tool["function"].__doc__)
        else:
            md_content.append("No docstring found")
        md_content.append("```")
        md_content.append("")

        md_content.append("---")
        md_content.append("")

    # Summary
    md_content.append("## Summary")
    md_content.append("")
    md_content.append(f"Total MCP tools documented: **{len(tools)}**")
    md_content.append("")
    md_content.append(
        "These are the **actual docstrings** generated by the `@auto_docstring` decorator."
    )
    md_content.append("The decorator automatically:")
    md_content.append("- Extracts field descriptions from Pydantic models")
    md_content.append("- Generates Google-style docstring format")
    md_content.append("- Documents input parameters with types and requirements")
    md_content.append("- Documents return values with types and descriptions")
    md_content.append(
        "- Uses the CORRECT model names (GetParameterInput, not ParameterDetailsInput)"
    )
    md_content.append(
        "- Shows union types properly (List[ParameterBase | Parameter], not List[unknown])"
    )
    md_content.append("- Makes it clear that inputs are JSON objects")
    md_content.append("")

    return "\n".join(md_content)


def main():
    """Main function to generate documentation."""
    print("🔍 Generating ACTUAL @auto_docstring output...")

    try:
        tools = get_auto_docstring_output()
        print(f"📊 Found {len(tools)} MCP tools")

        print("📝 Generating markdown documentation...")
        md_docs = generate_markdown_documentation(tools)

        # Write documentation file
        with open("MCP_TOOLS_AUTO_DOCSTRING_OUTPUT.md", "w") as f:
            f.write(md_docs)

        print("✅ Documentation generated:")
        print("   - MCP_TOOLS_AUTO_DOCSTRING_OUTPUT.md")

        # Print summary
        print("\n📋 Tools found:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool['name']} - {tool['endpoint']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
