import os
from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.utils import connect_to_database
from talk_with_fews.utils.schema_utils import extract_db_schema_as_dict
import duckdb
from talk_with_fews.tools.webservice.ingest_locations import ingest_locations
from talk_with_fews.tools.webservice.ingest_parameters import ingest_parameters


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


# Shared/cached context globals
_db_connection = None
_schema = None
_cache_FewsWebServices_db = None
_ingest_locations_output = None
_ingest_parameters_output = None


def get_runtime_ctx() -> RunContext:
    """
    Returns a RunContext[Deps] with a shared database connection and schema.
    Uses FEWS_DB_PATH env var or defaults to './fews.db'.
    """
    global \
        _db_connection, \
        _schema, \
        _cache_FewsWebServices_db, \
        _ingest_locations_output, \
        _ingest_parameters_output
    db_path = os.environ.get("FEWS_DB_PATH", "./fews.db")
    webservice_url = os.environ.get("FEWS_WEB_SERVICE_URL", None)
    if webservice_url.endswith("/"):
        webservice_url = webservice_url[:-1]

    if _db_connection is None:
        _db_connection = connect_to_database(db_path)
    if _schema is None:
        _schema = extract_db_schema_as_dict(db_path)
    if _cache_FewsWebServices_db is None:
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

    deps = Deps(db_path=db_path, db_connection=_db_connection)
    deps.webservice_url = webservice_url
    deps.schema = _schema
    # for now this is limited to the session
    deps.cache_FewsWebServices_db = _cache_FewsWebServices_db
    # TODO: not yet happy with this, should be a tool, but also run on startup? then it shouldn't be a tool?
    deps.ingest_locations_output = _ingest_locations_output
    deps.ingest_parameters_output = _ingest_parameters_output
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
