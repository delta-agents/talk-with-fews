import json
import os
from pathlib import Path
import warnings
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
            f"Failed to get HTTP request context {e}, reverting to default settings."
        )
        db_path = os.environ.get("FEWS_DB_PATH", "data/digiflow.db3.db")
        webservice_url = os.environ.get("FEWS_WEB_SERVICE_URL", None)
        user_settings = {
            "client_id": "test-no-auth",
            "FEWS_DB_PATH": db_path,
            "FEWS_WEB_SERVICE_URL": webservice_url,
        }
    else:
        authorization = request.headers.get("Authorization", None)
        if authorization is not None and authorization.startswith("Bearer "):
            authorization = authorization[len("Bearer ") :]
            user_settings = verifier.tokens[authorization]
        else:
            raise ValueError("Missing or invalid Authorization header")
    finally:
        return user_settings


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


# Shared/cached context globals

_empty_user_config = dict(
    _db_connection=None,
    _schema=None,
    _cache_FewsWebServices_db=None,
    _ingest_locations_output=None,
    _ingest_parameters_output=None,
    _cache_fews_schemas_dir=None,
)
_cached_configs = {}


def get_runtime_ctx(user_settings: dict) -> RunContext:
    """
    Returns a RunContext[Deps] with a shared database connection and schema.
    Uses FEWS_DB_PATH env var or defaults to './fews.db'.
    """

    global _cached_configs
    # if we know of the user we retrieve stored variables
    client_id = user_settings["client_id"]
    if client_id in _cached_configs:
        _db_connection = _cached_configs[client_id]["_db_connection"]
        _schema = _cached_configs[client_id]["_schema"]
        _cache_FewsWebServices_db = _cached_configs[client_id][
            "_cache_FewsWebServices_db"
        ]
        _ingest_locations_output = _cached_configs[client_id][
            "_ingest_locations_output"
        ]
        _ingest_parameters_output = _cached_configs[client_id][
            "_ingest_parameters_output"
        ]
        _cache_fews_schemas_dir = _cached_configs[client_id]["_cache_fews_schemas_dir"]
    else:
        # first time we see this user, so we create a new entry
        _cached_configs[client_id] = _empty_user_config.copy()
        _db_connection = None
        _schema = None
        _cache_FewsWebServices_db = None
        _ingest_locations_output = None
        _ingest_parameters_output = None
        _cache_fews_schemas_dir = None

    #### old way of getting settings from env vars
    # db_path = os.environ.get("FEWS_DB_PATH", "./fews.db")
    # webservice_url = os.environ.get("FEWS_WEB_SERVICE_URL", None)
    ### we now get these from the user settings, which are tied to the static token used
    db_path = user_settings["FEWS_DB_PATH"]

    if _db_connection is None:
        _db_connection = connect_to_database(db_path)

    if _schema is None:
        _schema = extract_db_schema_as_dict(db_path)

    # handle webservice URL
    webservice_url = user_settings["FEWS_WEB_SERVICE_URL"]

    # dev option to disable webservice ingestion

    disable_cache_FewsWebServices_db = os.environ.get(
        "DEV_DISABLE_WEBSERVICE_INGEST", "false"
    ).lower() in ("true", "1", "yes")
    if webservice_url is not None and webservice_url.endswith("/"):
        webservice_url = webservice_url[:-1]

    # TODO: monitor memory if this is okay for large databases
    if _cache_FewsWebServices_db is None and not disable_cache_FewsWebServices_db:
        _cache_FewsWebServices_db = duckdb.connect(database=":memory:", read_only=False)
        _cache_FewsWebServices_db.execute("INSTALL spatial;")
        _cache_FewsWebServices_db.execute("LOAD spatial;")

        # Ingest existing data
        _ingest_locations_output = ingest_locations(
            webservice_url, _cache_FewsWebServices_db
        )
        _ingest_parameters_output = ingest_parameters(
            webservice_url, _cache_FewsWebServices_db
        )
        _cache_FewsWebServices_db = setup_series_headers_table(
            _cache_FewsWebServices_db
        )

    # handle validation
    if _cache_fews_schemas_dir is None:
        _cache_fews_schemas_dir = os.environ.get(
            "FEWS_SCHEMAS_DIR", "data/fews_schemas"
        )

    # combine all three into a Deps object
    deps = Deps(db_path=db_path, db_connection=_db_connection)
    deps.webservice_url = webservice_url
    deps.schema = _schema
    # for now this is limited to the session
    deps.cache_FewsWebServices_db = _cache_FewsWebServices_db
    deps.ingest_locations_output = _ingest_locations_output
    deps.ingest_parameters_output = _ingest_parameters_output
    deps.cache_fews_schemas_dir = _cache_fews_schemas_dir

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
