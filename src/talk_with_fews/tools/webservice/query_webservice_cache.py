import duckdb
from pydantic_ai import RunContext, ModelRetry

from talk_with_fews.models.config.sql_query import SQLQueryInput, SQLQueryOutput
from talk_with_fews.models.base import Deps

from talk_with_fews.utils.logging_utils import log_tool_call, logger
from talk_with_fews.utils.schema_utils import (
    create_schema_info_dict,
    diagnose_sql_error,
)


@log_tool_call
async def query_webservice_cache(
    ctx: RunContext[Deps], input: SQLQueryInput
) -> SQLQueryOutput:
    """
    Execute SQL queries against the cached FEWS webservice database (DuckDB).

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
    To return geometry data: use ST_AsText(geom) for WGS84 or ST_AsText(ST_Transform(geom, 'EPSG:4326', 'EPSG:28992')) for RD.

    Args:
        ctx: RunContext with database connection
        input: SQLQueryInput containing the query to execute

    Returns:
        SQLQueryOutput: Results of the query with column names
    """
    try:
        # Execute the query
        connection: duckdb.DuckDBPyConnection = ctx.deps.cache_FewsWebServices_db
        cursor = connection.cursor()
        cursor.execute(input.query)

        # Extract results and column names
        column_names = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )
        results = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        # Return the query results
        return SQLQueryOutput(
            results=results,
            column_names=column_names,
            row_count=len(results),
            query_executed=input.query,
        )
    except duckdb.Error as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(f"SQL Error: {error_msg} - Query: {input.query}")

        # Attempt to diagnose common errors using schema_utils.diagnose_sql_error
        if hasattr(ctx.deps, "schema") and ctx.deps.schema:
            schema_info = create_schema_info_dict(ctx.deps.schema)
            error_diagnosis = diagnose_sql_error(str(e), input.query, schema_info)
            if error_diagnosis:
                error_msg += f" - {error_diagnosis}"

        raise ModelRetry(error_msg)
