import json
import os
from pathlib import Path
import warnings
from dataclasses import dataclass
from typing import Any, Optional
from dotenv import load_dotenv
from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.utils import connect_to_database
from talk_with_fews.utils.schema_utils import extract_db_schema_as_dict
import duckdb
from talk_with_fews.tools.webservice.ingest_locations import ingest_locations
from talk_with_fews.tools.webservice.ingest_parameters import ingest_parameters
from talk_with_fews.tools.webservice.ingest_series_headers import (
    ingest_all_series_headers,
)
from talk_with_fews.utils.logging_utils import logger
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request


def setup_env():
    """Load environment variables from a .env file located in the 'env' directory."""
    env_dir = Path(__file__).parent.parent.parent.parent / "env"
    load_dotenv(dotenv_path=env_dir / ".env")
    return json.load(
        open(env_dir / os.getenv("STATIC_TOKENS_FILE", ".static_tokens_example.json"))
    )


def get_user_settings(verifier) -> dict:
    """ "
    Extract user settings from the Authorization header using the provided verifier.
    This allows the user tools to have user specific settings
    """
    # maybe could be improved using `get_access_token` from `fastmcp.server.dependencies`
    try:
        request: Request = get_http_request()
    except RuntimeError as e:
        # allow debugging and testing without an HTTP request context
        warnings.warn(
            f"Failed to get HTTP request context {e}, reverting to environment variables."
        )
        db_path = os.environ.get("FEWS_DB_PATH")
        if not db_path:
            raise ValueError(
                "FEWS_DB_PATH environment variable not set. "
                "Required for testing without HTTP context."
            )
        webservice_url = os.environ.get("FEWS_WEB_SERVICE_URL", None)
        user_settings = {
            "client_id": "test-no-auth",
            "FEWS_DB_PATH": db_path,
            "FEWS_CONFIG_NAME": "test-config",
            "FEWS_WEB_SERVICE_URL": webservice_url,
            "FEWS_WEB_SERVICE_NAME": "test-web-service",
        }
    else:
        authorization = request.headers.get("Authorization", None)
        if authorization is not None and authorization.startswith("Bearer "):
            authorization = authorization[len("Bearer ") :]
            user_settings = verifier.tokens[authorization]
        else:
            raise ValueError("Missing or invalid Authorization header")

    # Validate paths before returning
    # FEWS_DB_PATH is required and must exist
    db_path = user_settings.get("FEWS_DB_PATH")
    if not db_path:
        raise ValueError(
            "FEWS_DB_PATH not configured in user settings. "
            "Please check your authentication token configuration."
        )
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"FEWS configuration database not found: {db_path}\n"
            f"Please check the FEWS_DB_PATH setting in your user configuration."
        )

    # FEWS_WEB_SERVICE_URL is optional, no validation needed

    return user_settings


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


@dataclass
class UserContextCache:
    """Cache for a single user's runtime context."""

    db_connection: Optional[Any] = None
    schema: Optional[dict] = None
    cache_FewsWebServices_db: Optional[Any] = None
    ingest_locations_output: Optional[Any] = None
    ingest_parameters_output: Optional[Any] = None
    ingest_all_series_headers_output: Optional[Any] = None
    cache_fews_schemas_dir: Optional[str] = None


class ContextCacheManager:
    """Manages cached contexts for multiple users."""

    def __init__(self):
        self._caches: dict[str, UserContextCache] = {}

    def get_or_create(self, client_id: str) -> UserContextCache:
        """Get cached context for a client or create new one."""
        if client_id not in self._caches:
            self._caches[client_id] = UserContextCache()
        return self._caches[client_id]

    def clear(self, client_id: str = None):
        """Clear cache for specific user or all users."""
        if client_id:
            self._caches.pop(client_id, None)
        else:
            self._caches.clear()


# Global cache manager
_cache_manager = ContextCacheManager()


def _get_cached_context(client_id: str) -> UserContextCache:
    """
    Get cached context for a client, or create new empty cache entry.

    Args:
        client_id: Unique identifier for the client

    Returns:
        UserContextCache object with cached values
    """
    return _cache_manager.get_or_create(client_id)


def _setup_database_connection(db_path: str, cached_connection):
    """
    Setup database connection if needed and enabled.

    Args:
        db_path: Path to the FEWS configuration database
        cached_connection: Previously cached connection (if any)

    Returns:
        Database connection or None
    """
    if cached_connection is not None:
        return cached_connection

    # Check if database connection is enabled
    # Behavior table documented in get_runtime_ctx
    enable_db_connection = os.environ.get(
        "DEV_DISABLE_CONFIG_DB", "false"
    ).lower() not in ("true", "1", "yes")

    if enable_db_connection:
        return connect_to_database(db_path)
    return None


def _setup_webservice_cache(
    webservice_url: str | None, cached_db, enable_webservice_ingest: bool
) -> tuple:
    """
    Setup webservice cache database and optionally ingest data.

    Args:
        webservice_url: URL for FEWS webservice (or None)
        cached_db: Previously cached database connection (if any)
        enable_webservice_ingest: Whether to ingest locations/parameters/series_headers

    Returns:
        Tuple of (cache_db, locations_output, parameters_output, series_headers_output)
    """
    # Return cached values if available
    if cached_db is not None:
        return cached_db, None, None, None

    # No webservice URL provided
    if webservice_url is None:
        return None, None, None, None

    # Create in-memory DuckDB database
    cache_db = duckdb.connect(database=":memory:", read_only=False)
    cache_db.execute("INSTALL spatial;")
    cache_db.execute("LOAD spatial;")

    # Optionally ingest data (this is the slow part)
    locations_output = None
    parameters_output = None
    series_headers_output = None
    if enable_webservice_ingest:
        locations_output = ingest_locations(webservice_url, cache_db)
        parameters_output = ingest_parameters(webservice_url, cache_db)
        # Setup the series_headers table (requires locations and parameters tables)
        cache_db = setup_series_headers_table(cache_db)

        # Check if series headers ingestion is enabled
        # Behavior controlled by DEV_DISABLE_SERIES_HEADERS_INGEST environment variable:
        # | DEV_DISABLE_SERIES_HEADERS_INGEST | enable_series_headers_ingest | Result                    |
        # |-----------------------------------|------------------------------|---------------------------|
        # | not set (default)                 | True                         | Full ingestion (default)  |
        # | "false"                           | True                         | Full ingestion            |
        # | "true" / "1" / "yes"              | False                        | No ingestion (fast mode)  |
        enable_series_headers_ingest = os.environ.get(
            "DEV_DISABLE_SERIES_HEADERS_INGEST", "false"
        ).lower() not in ("true", "1", "yes")

        # Additional check: Skip bulk ingestion in test mode unless explicitly enabled
        # This prevents expensive bulk ingestion during general testing
        skip_bulk_ingestion_in_tests = os.environ.get(
            "SKIP_BULK_SERIES_HEADERS_IN_TESTS", "true"
        ).lower() in ("true", "1", "yes")

        # Skip bulk ingestion if we're in test mode and it's not explicitly enabled
        if skip_bulk_ingestion_in_tests and os.environ.get("PYTEST_CURRENT_TEST"):
            enable_series_headers_ingest = False
            logger.info("Skipping bulk series headers ingestion in test mode")

        if enable_series_headers_ingest:
            # Get all parameter and location IDs for bulk ingestion
            parameter_ids = [
                row[0]
                for row in cache_db.execute("SELECT id FROM parameters").fetchall()
            ]
            location_ids = [
                row[0]
                for row in cache_db.execute(
                    "SELECT locationId FROM locations"
                ).fetchall()
            ]

            logger.info(
                f"Starting bulk series headers ingestion for {len(parameter_ids)} parameters and {len(location_ids)} locations"
            )
            series_headers_output = ingest_all_series_headers(
                webservice_url=webservice_url,
                cache_FewsWebServices_db=cache_db,
                parameter_ids=parameter_ids,
                location_ids=location_ids,
            )
            logger.info(
                f"Bulk series headers ingestion completed: {series_headers_output.description}"
            )
        else:
            logger.info(
                "Series headers ingestion disabled via DEV_DISABLE_SERIES_HEADERS_INGEST"
            )

    return cache_db, locations_output, parameters_output, series_headers_output


def get_runtime_ctx(user_settings: dict) -> RunContext:
    """
    Returns a RunContext[Deps] with a shared database connection and schema.

    Args:
        user_settings: Dictionary containing user-specific settings including:
            - FEWS_DB_PATH: Path to the FEWS configuration database (validated in get_user_settings)
            - FEWS_WEB_SERVICE_URL: Optional URL for FEWS webservice
            - client_id: Unique identifier for the user/client

    Returns:
        RunContext with initialized dependencies (database, schema, webservice cache)

    Note:
        - Database connections and schemas are cached per client_id
        - Use DEV_DISABLE_CONFIG_DB=true to skip database connection (development)
        - Use DEV_DISABLE_WEBSERVICE_INGEST=true to skip slow webservice data ingestion (development)
        - Use DEV_DISABLE_SERIES_HEADERS_INGEST=true to skip series headers ingestion (development)
    """

    # Extract user settings
    client_id = user_settings["client_id"]
    db_path = user_settings["FEWS_DB_PATH"]  # Already validated in get_user_settings()
    config_name = user_settings.get("FEWS_CONFIG_NAME")
    webservice_url = user_settings.get("FEWS_WEB_SERVICE_URL")
    webservice_name = user_settings.get("FEWS_WEB_SERVICE_NAME")

    # Clean webservice URL (remove trailing slash)
    if webservice_url and webservice_url.endswith("/"):
        webservice_url = webservice_url[:-1]

    # Get or create cached context for this client
    cache = _get_cached_context(client_id)

    # Setup database connection (uses cached value if available)
    # Behavior controlled by DEV_DISABLE_CONFIG_DB environment variable:
    # | DEV_DISABLE_CONFIG_DB | enable_db_connection | Result                              |
    # |-----------------------|----------------------|-------------------------------------|
    # | not set (default)     | True                 | Connect to config DB (default)      |
    # | "false"               | True                 | Connect to config DB                |
    # | "true" / "1" / "yes"  | False                | No config DB connection (fast mode) |
    db_connection = _setup_database_connection(db_path, cache.db_connection)

    # Extract database schema (always needed for LLM context)
    schema = cache.schema
    if schema is None:
        schema = extract_db_schema_as_dict(db_path)

    # Check if webservice data ingestion is enabled
    # Behavior controlled by DEV_DISABLE_WEBSERVICE_INGEST environment variable:
    # | DEV_DISABLE_WEBSERVICE_INGEST | enable_webservice_ingest | Result                    |
    # |-------------------------------|--------------------------|---------------------------|
    # | not set (default)             | True                     | Full ingestion (default)  |
    # | "false"                       | True                     | Full ingestion            |
    # | "true" / "1" / "yes"          | False                    | No ingestion (fast mode)  |
    enable_webservice_ingest = os.environ.get(
        "DEV_DISABLE_WEBSERVICE_INGEST", "false"
    ).lower() not in ("true", "1", "yes")

    # Setup webservice cache (creates in-memory DB, optionally ingests data)
    cache_db, locations_output, parameters_output, series_headers_output = (
        _setup_webservice_cache(
            webservice_url, cache.cache_FewsWebServices_db, enable_webservice_ingest
        )
    )

    # Get schemas directory for XML validation
    # Note: We don't validate it exists here - validator tools will check when needed
    schemas_dir = cache.cache_fews_schemas_dir
    if schemas_dir is None:
        schemas_dir = os.environ.get("FEWS_SCHEMAS_DIR", "data/fews_schemas")

    # Build dependencies object
    deps = Deps(db_path=db_path, db_connection=db_connection)
    deps.webservice_url = webservice_url
    deps.schema = schema
    deps.cache_FewsWebServices_db = cache_db
    deps.cache_fews_schemas_dir = schemas_dir
    deps.config_name = config_name
    deps.webservice_name = webservice_name

    # Update cache with new values
    cache.db_connection = db_connection
    cache.schema = schema
    cache.cache_FewsWebServices_db = cache_db
    cache.cache_fews_schemas_dir = schemas_dir

    return CtxWithDeps(deps)


def setup_series_headers_table(
    _cache_FewsWebServices_db: duckdb.DuckDBPyConnection,
) -> duckdb.DuckDBPyConnection:
    # Create series_headers table (empty initially, populated incrementally)
    _cache_FewsWebServices_db.execute("DROP TABLE IF EXISTS series_headers")
    _cache_FewsWebServices_db.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS series_headers_id_seq START 1 INCREMENT 1
        """
    )
    _cache_FewsWebServices_db.execute("""
        CREATE TABLE series_headers (
            id INTEGER PRIMARY KEY,
            type VARCHAR,
            moduleInstanceId VARCHAR,
            locationId VARCHAR,
            parameterId VARCHAR,
            timeStepUnit VARCHAR,
            timeStepMultiplier INTEGER,
            missVal DOUBLE,
            timeZone VARCHAR,
            qualifiers VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Foreign key constraints
            FOREIGN KEY (locationId) REFERENCES locations(locationId),
            FOREIGN KEY (parameterId) REFERENCES parameters(id)
        )
    """)

    # Create indexes for performance
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_parameterId ON series_headers(parameterId)"
    )
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_locationId ON series_headers(locationId)"
    )
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_moduleInstanceId ON series_headers(moduleInstanceId)"
    )
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_type ON series_headers(type)"
    )
    return _cache_FewsWebServices_db
