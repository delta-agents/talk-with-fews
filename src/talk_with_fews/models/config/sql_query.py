"""
Pydantic models for the FEWS Configuration Agent.

This module defines the models used by the agent to query and analyze FEWS configurations.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from talk_with_fews.models.base import LaxBaseModel


class SQLQueryInput(LaxBaseModel):
    """
    Input for SQL query.

    Attributes:
        query: SQL query to execute
    """

    query: str = Field(..., description="SQL query to execute")


class SQLQueryOutput(BaseModel):
    """
    Output from SQL query.

    Attributes:
        results: Query results as list of dictionaries
        column_names: Names of columns in the result set, preserving original order
        row_count: Number of rows returned by the query
        query_executed: The SQL query that was executed
    """

    results: List[Dict[str, Any]] = Field(..., description="Results of the SQL query")
    column_names: List[str] = Field(
        ..., description="Column names of the result set in original order"
    )
    row_count: int = Field(..., description="Number of rows returned by the query")
    query_executed: str = Field(..., description="The SQL query that was executed")
