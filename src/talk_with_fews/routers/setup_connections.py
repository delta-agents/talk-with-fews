import os
from pydantic_ai import RunContext
from talk_with_fews.models.base import Deps
from talk_with_fews.utils.utils import connect_to_database
from talk_with_fews.utils.schema_utils import extract_db_schema_as_dict
import duckdb
from talk_with_fews.routers.setup_webservice import get_locations, get_parameters


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


# Shared/cached context globals
_db_connection = None
_schema = None
_cache_FewsWebServices_db = None


def get_runtime_ctx() -> RunContext:
    """
    Returns a RunContext[Deps] with a shared database connection and schema.
    Uses FEWS_DB_PATH env var or defaults to './fews.db'.
    """
    global _db_connection, _schema, _cache_FewsWebServices_db
    db_path = os.environ.get("FEWS_DB_PATH", "./fews.db")
    webservice_url = os.environ.get("FEWS_WEB_SERVICE_URL", None)
    if _db_connection is None:
        _db_connection = connect_to_database(db_path)
    if _schema is None:
        _schema = extract_db_schema_as_dict(db_path)
    if _cache_FewsWebServices_db is None:
        _cache_FewsWebServices_db = duckdb.connect(database=":memory:", read_only=False)
        get_locations(webservice_url, _cache_FewsWebServices_db)
        get_parameters(webservice_url, _cache_FewsWebServices_db)

    deps = Deps(db_path=db_path, db_connection=_db_connection)
    deps.webservice_url = webservice_url
    deps.schema = _schema
    # for now this is limited to the session
    deps.cache_FewsWebServices_db = _cache_FewsWebServices_db
    return CtxWithDeps(deps)
