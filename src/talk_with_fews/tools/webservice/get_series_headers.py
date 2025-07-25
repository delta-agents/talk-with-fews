"""
Get series headers with incremental caching from FEWS webservice.

This tool retrieves series headers using an incremental caching approach. It first checks
the local DuckDB cache, and if data is not found, it triggers ingestion from the webservice.
"""

from typing import List, Dict
import duckdb
import pandas as pd
from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.models.get_series_headers import (
    GetSeriesHeadersInput,
    GetSeriesHeadersOutput,
)
from talk_with_fews.tools.webservice.ingest_series_headers import ingest_series_headers
from talk_with_fews.utils.logging_utils import log_tool_call


def get_series_headers_with_details(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_id: str = None,
    location_id: str = None,
) -> pd.DataFrame:
    """Query series headers with complete location and parameter information"""

    query = """
        SELECT
            sh.id,
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


def get_available_filters(
    cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
    parameter_id: str = None,
    location_id: str = None,
) -> Dict[str, List[str]]:
    """Get available filter options for the query results"""

    available_filters = {}

    if parameter_id:
        # For parameter query, show available locations and model types
        locations = cache_FewsWebServices_db.execute(
            """
            SELECT DISTINCT locationId
            FROM series_headers
            WHERE parameterId = ?
            ORDER BY locationId
            LIMIT 10
        """,
            [parameter_id],
        ).fetchall()

        model_types = cache_FewsWebServices_db.execute(
            """
            SELECT DISTINCT
                CASE
                    WHEN moduleInstanceId LIKE '%hist%' THEN 'historical'
                    WHEN moduleInstanceId LIKE '%fcst%' THEN 'forecast'
                    ELSE 'other'
                END as model_type
            FROM series_headers
            WHERE parameterId = ?
            ORDER BY model_type
        """,
            [parameter_id],
        ).fetchall()

        available_filters["locations"] = [row[0] for row in locations]
        available_filters["model_types"] = [
            row[0] for row in model_types if row[0] != "other"
        ]

    elif location_id:
        # For location query, show available parameters and model types
        parameters = cache_FewsWebServices_db.execute(
            """
            SELECT DISTINCT parameterId
            FROM series_headers
            WHERE locationId = ?
            ORDER BY parameterId
            LIMIT 10
        """,
            [location_id],
        ).fetchall()

        model_types = cache_FewsWebServices_db.execute(
            """
            SELECT DISTINCT
                CASE
                    WHEN moduleInstanceId LIKE '%hist%' THEN 'historical'
                    WHEN moduleInstanceId LIKE '%fcst%' THEN 'forecast'
                    ELSE 'other'
                END as model_type
            FROM series_headers
            WHERE locationId = ?
            ORDER BY model_type
        """,
            [location_id],
        ).fetchall()

        available_filters["parameters"] = [row[0] for row in parameters]
        available_filters["model_types"] = [
            row[0] for row in model_types if row[0] != "other"
        ]

    return available_filters


def generate_follow_up_suggestions(
    parameter_id: str = None, location_id: str = None, count: int = 0
) -> List[str]:
    """Generate user-friendly follow-up suggestions"""

    suggestions = []

    if parameter_id:
        if count > 10:
            suggestions.append(
                f"Get series for specific location from the available {count} locations"
            )
        suggestions.append("Filter by historical model data")
        suggestions.append("Analyze spatial distribution of series")

    elif location_id:
        if count > 10:
            suggestions.append(
                f"Get series for specific parameter from the available {count} parameters"
            )
        suggestions.append("Analyze time ranges and data coverage")
        suggestions.append("Compare with other locations in the region")

    # Limit to 3 suggestions
    return suggestions[:3]


@log_tool_call
async def get_series_headers(
    ctx: RunContext[Deps], input: GetSeriesHeadersInput
) -> GetSeriesHeadersOutput:
    """
    Retrieve series headers with incremental caching from FEWS webservice.

    This tool implements the incremental caching strategy: first check local cache,
    then trigger ingestion if needed, and return minimal but meaningful output.

    Args:
        ctx: RunContext with database connection
        input: GetSeriesHeadersInput containing parameter_id OR location_id

    Returns:
        GetSeriesHeadersOutput with series headers summary and follow-up suggestions
    """

    # Validate input
    if input.parameter_id and input.location_id:
        raise ValueError("Cannot specify both parameter_id and location_id")
    if not input.parameter_id and not input.location_id:
        raise ValueError("Must specify either parameter_id or location_id")

    cache_FewsWebServices_db = ctx.deps.cache_FewsWebServices_db
    webservice_url = ctx.deps.webservice_url

    # Check if we have data cached
    if input.parameter_id:
        series_headers_retrieved = cache_FewsWebServices_db.execute(
            """
            SELECT series_headers_retrieved FROM parameters WHERE id = ?
            """,
            [input.parameter_id],
        ).fetchone()[0]

        if not series_headers_retrieved:
            # No data cached - trigger ingestion
            await ingest_series_headers(
                webservice_url=webservice_url,
                cache_FewsWebServices_db=cache_FewsWebServices_db,
                parameter_id=input.parameter_id,
            )
            cache_FewsWebServices_db.execute(
                """
                UPDATE parameters SET series_headers_retrieved = TRUE WHERE id = ?
            """,
                [input.parameter_id],
            )

        # Query cached data
        df_results = get_series_headers_with_details(
            cache_FewsWebServices_db, parameter_id=input.parameter_id
        )

        # Generate summary
        summary = f"Found timeseries for {input.parameter_id} across {df_results['locationId'].nunique()} locations"

    else:  # location_id
        series_headers_retrieved = cache_FewsWebServices_db.execute(
            """
            SELECT series_headers_retrieved FROM locations WHERE locationId = ?
            """,
            [input.location_id],
        ).fetchone()[0]

        if not series_headers_retrieved:
            # No data cached - trigger ingestion
            await ingest_series_headers(
                webservice_url=webservice_url,
                cache_FewsWebServices_db=cache_FewsWebServices_db,
                location_id=input.location_id,
            )
            cache_FewsWebServices_db.execute(
                """
                UPDATE locations SET series_headers_retrieved = TRUE WHERE locationId = ?
            """,
                [input.location_id],
            )
        # Query cached data
        df_results = get_series_headers_with_details(
            cache_FewsWebServices_db, location_id=input.location_id
        )

        # Get location name for summary
        location_name = cache_FewsWebServices_db.execute(
            """
            SELECT shortName FROM locations WHERE locationId = ?
        """,
            [input.location_id],
        ).fetchone()
        location_display = location_name[0] if location_name else input.location_id

        # Generate summary
        summary = f"Found {df_results['parameterId'].nunique()} parameters at location {location_display}."

    # Generate sample IDs
    sample_ids = df_results.head().to_markdown(index=False)

    # Get available filters
    available_filters = get_available_filters(
        cache_FewsWebServices_db, input.parameter_id, input.location_id
    )

    # TODO: readd generate_follow_up_suggestions
    # Generate follow-up suggestions
    # follow_up_suggestions = generate_follow_up_suggestions(
    #     input.parameter_id, input.location_id, len(results)
    # )
    follow_up_suggestions = ["No follow-up suggestions available yet."]

    return GetSeriesHeadersOutput(
        count=len(df_results),
        summary=summary,
        sample_ids=sample_ids,
        available_filters=available_filters,
        follow_up_suggestions=follow_up_suggestions,  # Placeholder for follow-up suggestions
    )
