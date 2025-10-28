"""
Get series headers with incremental caching from FEWS webservice.

This tool retrieves series headers using an incremental caching approach. It first checks
the local DuckDB cache, and if data is not found, it triggers ingestion from the webservice.
"""

from typing import List, Dict
import duckdb
import pandas as pd
from pydantic_ai import ModelRetry, RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.models.webservice.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.utils.logging_utils import log_tool_call


def get_series_headers_with_details(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_id: str = None,
    location_id: str = None,
) -> pd.DataFrame:
    """Query series headers with complete location and parameter information"""

    query = """
        SELECT
            sh.type,
            sh.moduleInstanceId,
            sh.locationId,
            sh.parameterId,
            sh.timeStepUnit,
            sh.timeStepMultiplier,
            sh.missVal,
            sh.timeZone,
            sh.qualifiers,
            sh.created_at,
            -- Location details
            l.shortName as location_name,
            l.lat as location_lat,
            l.lon as location_lon,
            -- Parameter details
            p.name as parameter_name,
            p.unit as parameter_unit,
            p.parameter_type as parameter_type
        FROM series_headers sh
        JOIN locations l ON sh.locationId = l.locationId
        JOIN parameters p ON sh.parameterId = p.id
    """

    params = []
    conditions = []

    if parameter_id:
        conditions.append("sh.parameterId = ?")
        params.append(parameter_id)

    if location_id:
        conditions.append("sh.locationId = ?")
        params.append(location_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY sh.locationId, sh.parameterId"

    return cache_FewsWebServices_db.execute(query, params).df()


def get_available_ids(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_id: str = None,
    location_id: str = None,
) -> Dict[str, List[str]]:
    """Get available IDs for follow-up queries"""

    if parameter_id:
        # For parameter query, show available locations
        locations = cache_FewsWebServices_db.execute(
            "SELECT DISTINCT locationId FROM series_headers WHERE parameterId = ? ORDER BY locationId",
            [parameter_id],
        ).fetchall()
        return {"locations": [row[0] for row in locations]}

    else:  # location_id
        # For location query, show available parameters
        parameters = cache_FewsWebServices_db.execute(
            "SELECT DISTINCT parameterId FROM series_headers WHERE locationId = ? ORDER BY parameterId",
            [location_id],
        ).fetchall()
        return {"parameters": [row[0] for row in parameters]}


@log_tool_call
async def get_series_headers(
    ctx: RunContext[Deps], input: GetSeriesHeadersInput
) -> GetSeriesHeadersOutput:
    """
    Discover available time series data by finding valid parameter-location combinations.

    This tool queries the pre-ingested series headers cache to find available combinations.
    All series headers are now ingested during server initialization for optimal performance.

    Examples:
    - "What parameters are available at location X?" -> use location_id="X"
    - "Which locations have parameter Y?" -> use parameter_id="Y"

    Use the returned available_ids to make targeted follow-up queries for specific data.

    Args:
        ctx: RunContext with database connection
        input: GetSeriesHeadersInput containing parameter_id OR location_id

    Returns:
        GetSeriesHeadersOutput with discovered series combinations and follow-up options
    """

    # Validate input
    if input.parameter_id and input.location_id:
        raise ModelRetry("Cannot specify both parameter_id and location_id")
    if not input.parameter_id and not input.location_id:
        raise ModelRetry("Must specify either parameter_id or location_id")

    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db

    # Check if cache database is available
    if cache_FewsWebServices_db is None:
        raise ModelRetry(
            "Webservice cache database not available. Please check webservice configuration."
        )

    # Query cached data directly (no on-demand ingestion needed)
    df_results = get_series_headers_with_details(
        cache_FewsWebServices_db,
        parameter_id=input.parameter_id,
        location_id=input.location_id,
    )

    # Convert DataFrame to dictionaries
    results = []
    for _, row in df_results.iterrows():
        series_dict = {
            "location_id": row["locationId"],
            "parameter_id": row["parameterId"],
            "parameter_name": row["parameter_name"],
            "location_name": row["location_name"],
            "time_step_unit": row["timeStepUnit"],
            "time_step_multiplier": row["timeStepMultiplier"],
            "module_instance_id": row["moduleInstanceId"],
            "type": row["type"],
            "parameter_unit": row["parameter_unit"],
        }
        results.append(series_dict)

    # Get available IDs for follow-up queries
    available_ids = get_available_ids(
        cache_FewsWebServices_db, input.parameter_id, input.location_id
    )

    # Generate actionable description
    if input.parameter_id:
        description = f"Found {len(results)} locations with parameter '{input.parameter_id}'. Use available_ids.locations for follow-up queries."
    else:
        location_display = (
            df_results["location_name"].iloc[0]
            if len(df_results) > 0
            else input.location_id
        )
        description = f"Found {len(results)} parameters at location '{location_display}'. Use available_ids.parameters for follow-up queries."

    return GetSeriesHeadersOutput(
        series_headers=results,
        description=description,
        available_ids=available_ids,
    )
