from pydantic_ai import ModelRetry, RunContext

from talk_with_fews.models.sql_query import SQLQueryInput
from talk_with_fews.models.base import Deps

from talk_with_fews.models.timeseries_search import (
    TimeSeriesSearchOutput,
    TimeSeriesSearchResult,
)
from talk_with_fews.tools.sql_query import execute_query
from talk_with_fews.utils.logging_utils import log_tool_call, logger


@log_tool_call
async def search_timeseries(
    ctx: RunContext[Deps], input: TimeSeriesSearchOutput
) -> TimeSeriesSearchOutput:
    """
    Search for time series sets by parameter, qualifier, module, or endpoint status.

    Args:
        ctx: RunContext with database connection
        input: TimeSeriesSearchInput containing search criteria

    Returns:
        TimeSeriesSearchOutput: Matching time series sets with formatted markdown content
    """
    # Check if we're filtering by endpoint status
    if input.endpoint is not None:
        # Create a more specific query that joins with the endpoints table
        query = """
            SELECT ts.id, ts.modins, ts.vtype, ts.parid, ts.qualifiers, ts.tstype, ts.timess,
                   CASE WHEN e.tss_id IS NOT NULL THEN 1 ELSE 0 END as is_endpoint
            FROM ts_sets ts
        """

        conditions = []

        # Join with endpoints table based on filter type
        if input.endpoint:
            query += " INNER JOIN endpoints e ON ts.id = e.tss_id"
        else:
            query += " LEFT JOIN endpoints e ON ts.id = e.tss_id WHERE e.tss_id IS NULL"

        # Add other conditions
        if input.parameter_id:
            conditions.append(f"ts.parid LIKE '%{input.parameter_id}%'")

        if input.qualifier_pattern:
            conditions.append(f"ts.qualifiers LIKE '%{input.qualifier_pattern}%'")

        if input.module_instance:
            conditions.append(f"ts.modins LIKE '%{input.module_instance}%'")

        # Add other conditions to the query
        if conditions:
            if not input.endpoint or input.endpoint:
                query += " WHERE " + " AND ".join(conditions)
            else:
                query += " AND " + " AND ".join(conditions)

        query += " ORDER BY ts.id"
    else:
        # Use the standard approach for non-endpoint filtering
        conditions = []

        if input.parameter_id:
            conditions.append(f"parid LIKE '%{input.parameter_id}%'")

        if input.qualifier_pattern:
            conditions.append(f"qualifiers LIKE '%{input.qualifier_pattern}%'")

        if input.module_instance:
            conditions.append(f"modins LIKE '%{input.module_instance}%'")

        if not conditions:
            logger.warning("search_timeseries called without any search criteria")
            raise ModelRetry("At least one search criterion is required")

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT ts.id, ts.modins, ts.vtype, ts.parid, ts.qualifiers, ts.tstype, ts.timess,
               CASE WHEN e.tss_id IS NOT NULL THEN 1 ELSE 0 END as is_endpoint
        FROM ts_sets ts
        LEFT JOIN endpoints e ON ts.id = e.tss_id
        WHERE {where_clause}
        ORDER BY ts.id
        """

    result = await execute_query(ctx, SQLQueryInput(query=query))

    # Convert results to TimeSeriesSearchResult objects
    time_series_results = []
    for row in result.results:
        # Create description using the standard template
        description = f"{row['modins']}|{row['vtype']}|{row['parid']}|{row['qualifiers']}|{row['tstype']}|{row['timess']}"
        is_endpoint = bool(row.get("is_endpoint", False))

        time_series = TimeSeriesSearchResult(
            id=row["id"],
            modins=row["modins"],
            vtype=row["vtype"],
            parid=row["parid"],
            qualifiers=row["qualifiers"],
            tstype=row["tstype"],
            timess=row["timess"],
            description=description,
            endpoint=is_endpoint,
        )
        time_series_results.append(time_series)

    # Generate markdown content
    markdown_content = f"""## Time Series Search Results
Found {len(time_series_results)} time series matching the criteria.

| ID | Module Instance | Type | Parameter | Qualifiers | Value Type | Time Step | Endpoint |
|----|----------------|------|-----------|------------|------------|-----------|----------|
"""

    for ts in time_series_results:
        is_endpoint = "✓" if ts.endpoint else ""
        markdown_content += f"| {ts.id} | {ts.modins} | {ts.tstype} | {ts.parid} | {ts.qualifiers} | {ts.vtype} | {ts.timess} | {is_endpoint} |\n"

    return TimeSeriesSearchOutput(
        results=time_series_results, markdown_content=markdown_content
    )
