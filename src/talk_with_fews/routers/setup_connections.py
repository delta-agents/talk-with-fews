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
from fastmcp.server.dependencies import get_http_request
from starlette.requests import Request
from datetime import datetime, timezone


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


def _ingest_all_series_headers(
    webservice_url: str, cache_db: duckdb.DuckDBPyConnection
):
    """
    Ingest series headers for all parameters using the series-aware approach.
    This finds all unique (parameter_id, location_id, module_instance_id) combinations
    and their individual first/last value times.
    """
    try:
        # Get all parameters from the database
        parameters = cache_db.execute("SELECT id FROM parameters").fetchall()
        print(f"Found {len(parameters)} parameters to process")

        total_inserted = 0

        # Step 1: Discover series combinations by parameter (async parallel processing)
        print(
            "Step 1: Discovering series combinations by parameter (async parallel)..."
        )

        try:
            import asyncio
            from talk_with_fews.tools.webservice.ingest_series_headers import (
                discover_all_series_async,
            )

            # Get all parameters
            parameter_ids = [param_row[0] for param_row in parameters]

            print(
                f"Processing {len(parameter_ids)} parameters with async HTTP client..."
            )

            # Run the async discovery
            series_results = asyncio.run(
                discover_all_series_async(
                    webservice_url=webservice_url,
                    parameter_ids=parameter_ids,
                    max_concurrent=20,  # Limit concurrent requests
                )
            )

            # Insert all discovered series into database
            for param_id, series_data in series_results.items():
                for series_key, data in series_data.items():
                    module_instance_id, location_id, param_id = series_key

                    # Insert series with basic metadata and data_available flag
                    cache_db.execute(
                        """
                        INSERT INTO series_headers (
                            id, type, moduleInstanceId, locationId, parameterId,
                            timeStepUnit, timeStepMultiplier, missVal, timeZone, qualifiers,
                            first_value_time, last_value_time, data_available, created_at
                        ) VALUES (nextval('series_headers_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        [
                            data.get("type"),
                            module_instance_id,
                            location_id,
                            param_id,
                            data.get("timeStepUnit"),
                            data.get("timeStepMultiplier"),
                            data.get("missVal"),
                            data.get("timeZone"),
                            data.get("qualifiers"),
                            data.get("firstValueTime"),
                            data.get("lastValueTime"),
                            True,  # Assume all discovered series have data initially, Step 2 will filter out empty ones
                            datetime.now(timezone.utc),
                        ],
                    )
                    total_inserted += 1
                    if total_inserted % 100 == 0:
                        print(f"  Inserted {total_inserted} series...")

        except Exception as e:
            print(f"Error discovering series combinations: {e}")
            return

        print(f"Step 1 complete: Discovered {total_inserted} series combinations")

        # Skip step 2 for now - instead do this on the fly.
        # Step 2: Find actual date ranges for discovered series using showStatistics=True
        # print("Step 2: Finding actual date ranges for discovered series...")

        # try:
        #     import asyncio
        #     from talk_with_fews.tools.webservice.ingest_series_headers import (
        #         discover_all_series_async,
        #     )

        #     # Get unique parameters from the discovered series combinations
        #     unique_parameters = cache_db.execute("""
        #         SELECT DISTINCT parameterId
        #         FROM series_headers
        #         WHERE data_available = true
        #     """).fetchall()

        #     print(
        #         f"Found {len(unique_parameters)} unique parameters to process for date ranges"
        #     )

        #     # Process parameters in batches to get actual date ranges
        #     async def process_parameter_for_dates(param_row):
        #         """Process a single parameter to get actual date ranges using showStatistics=True."""
        #         try:
        #             param_id = param_row[0]
        #             print(f"Processing parameter for dates: {param_id}")

        #             # Use discover_all_series_async with showStatistics=True to get actual date ranges
        #             # This will NOT trigger the full ingestion process, just get the statistics
        #             result = await discover_all_series_async(
        #                 webservice_url=webservice_url,
        #                 parameter_ids=[param_id],
        #                 show_statistics=True,
        #                 max_concurrent=1,  # Process one parameter at a time to avoid overwhelming the API
        #             )

        #             # Update the database with actual date ranges from the result
        #             updated_count = 0
        #             # The discover_all_series_async function returns keys with "params_" prefix
        #             result_key = f"params_{param_id}"
        #             if result_key in result:
        #                 for (
        #                     module_instance_id,
        #                     location_id,
        #                     param_id_key,
        #                 ), series_data in result[result_key].items():
        #                     if series_data.get("hasData", False):
        #                         # Update the existing series record with actual date ranges
        #                         cache_db.execute(
        #                             """
        #                             UPDATE series_headers
        #                             SET first_value_time = ?, last_value_time = ?, data_available = ?
        #                             WHERE moduleInstanceId = ? AND locationId = ? AND parameterId = ?
        #                         """,
        #                             [
        #                                 series_data.get("firstValueTime"),
        #                                 series_data.get("lastValueTime"),
        #                                 True,
        #                                 module_instance_id,
        #                                 location_id,
        #                                 param_id_key,
        #                             ],
        #                         )
        #                         updated_count += 1
        #                     else:
        #                         # Mark as no data
        #                         cache_db.execute(
        #                             """
        #                             UPDATE series_headers
        #                             SET data_available = ?
        #                             WHERE moduleInstanceId = ? AND locationId = ? AND parameterId = ?
        #                         """,
        #                             [
        #                                 False,
        #                                 module_instance_id,
        #                                 location_id,
        #                                 param_id_key,
        #                             ],
        #                         )

        #             print(
        #                 f"Parameter {param_id}: Updated {updated_count} series with actual date ranges"
        #             )
        #             return param_id, updated_count

        #         except Exception as e:
        #             print(f"Error processing parameter {param_row[0]} for dates: {e}")
        #             return param_row[0], 0

        #     # Process all parameters sequentially to avoid overwhelming the API
        #     async def run_date_range_processing():
        #         results = []
        #         for param_row in unique_parameters:
        #             result = await process_parameter_for_dates(param_row)
        #             results.append(result)
        #         return results

        #     print(
        #         f"Processing {len(unique_parameters)} parameters for actual date ranges..."
        #     )
        #     date_results = asyncio.run(run_date_range_processing())

        #     # Process results
        #     total_updated = 0
        #     successful_params = 0
        #     for param_id, updated_count in date_results:
        #         total_updated += updated_count
        #         if updated_count > 0:
        #             successful_params += 1
        #         print(f"Parameter {param_id}: {updated_count} series updated")

        #     print(
        #         f"Step 2 complete: Updated {total_updated} series with actual date ranges from {successful_params}/{len(unique_parameters)} parameters"
        #     )

        # except Exception as e:
        #     print(f"Error in Step 2: {e}")
        #     return

        # print(f"Successfully ingested {total_inserted} series headers")

    except Exception as e:
        print(f"Error in series headers ingestion: {e}")


def _save_database_to_file(
    cache_db: duckdb.DuckDBPyConnection, webservice_url: str
) -> str:
    """
    Save the in-memory DuckDB database to a file for debugging and investigation.

    Args:
        cache_db: The in-memory DuckDB connection
        webservice_url: The webservice URL to use in the filename

    Returns:
        Path to the saved database file
    """
    # Create a filename based on the webservice URL and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract service name from URL (e.g., "hdsr" from "http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHDSR")
    service_name = "unknown"
    if webservice_url:
        # Extract service name from URL path
        url_parts = webservice_url.split("/")
        for part in url_parts:
            if "FewsWebServices" in part:
                service_name = part.replace("FewsWebServices", "").lower()
                break

    # Create output directory
    output_dir = Path("data") / "webservice_cache"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename
    filename = f"fews_cache_{service_name}_{timestamp}.duckdb"
    filepath = output_dir / filename

    # Save the database to file
    cache_db.execute(f"EXPORT DATABASE '{filepath}'")

    print(f"Saved webservice cache to: {filepath}")
    return str(filepath)


def _setup_webservice_cache(
    webservice_url: str | None, cached_db, enable_webservice_ingest: bool
) -> tuple:
    """
    Setup webservice cache database and optionally ingest data.

    Args:
        webservice_url: URL for FEWS webservice (or None)
        cached_db: Previously cached database connection (if any)
        enable_webservice_ingest: Whether to ingest locations/parameters

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
    if enable_webservice_ingest:
        ingest_locations(webservice_url, cache_db)
        ingest_parameters(webservice_url, cache_db)
        # Setup the series_headers table (requires locations and parameters tables)
        skip_header_ingest = os.environ.get(
            "DEV_SKIP_HEADER_INGEST", "false"
        ).lower() in (
            "true",
            "1",
            "yes",
        )
        if skip_header_ingest:
            cache_db = setup_series_headers_table(cache_db)  # Re-create empty table
        else:
            # Ingest series headers data (requires locations and parameters to be ingested first)
            # We need to ingest series headers for all parameters to populate the cache
            print("Ingesting series headers for all parameters...")
            _ingest_all_series_headers(webservice_url, cache_db)
            ## Save the database to file for debugging and investigation
            ## Controlled by DEV_SAVE_WEBSERVICE_CACHE environment variable
            save_cache = os.environ.get(
                "DEV_SAVE_WEBSERVICE_CACHE", "false"
            ).lower() in (
                "true",
                "1",
                "yes",
            )
            if webservice_url and save_cache:
                _save_database_to_file(cache_db, webservice_url)

    return cache_db, None, None, None


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
        - Use DEV_SAVE_WEBSERVICE_CACHE=true to save in-memory databases to files for debugging (development)
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
    cache_db, _, _, _ = _setup_webservice_cache(
        webservice_url, cache.cache_FewsWebServices_db, enable_webservice_ingest
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
            first_value_time TIMESTAMP,
            last_value_time TIMESTAMP,
            data_available BOOLEAN DEFAULT FALSE,
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
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_first_value_time ON series_headers(first_value_time)"
    )
    _cache_FewsWebServices_db.execute(
        "CREATE INDEX idx_series_headers_last_value_time ON series_headers(last_value_time)"
    )
    return _cache_FewsWebServices_db
