from typing import Dict, Any, Optional
import sqlite3


class ToolCallTracker:
    """Class to track tool calls and their results.

    This class is used to maintain a history of tool calls and their outcomes,
    which can be useful for debugging and analysis.
    """

    def __init__(self):
        self.calls = []


class Deps:
    """
    Dependencies for the FEWS Configuration Agent.

    Attributes:
        db_connection: SQLite database connection
        db_path: Path to the SQLite database
        schema: Comprehensive database schema information
        tracker: Tool call tracker
    """

    def __init__(
        self,
        db_path: str = None,
        db_connection: sqlite3.Connection = None,
        tracker: ToolCallTracker = None,
    ):
        self.db_path = db_path
        self.db_connection = db_connection
        self.schema: Optional[Dict[str, Any]] = None
        self.tracker = tracker