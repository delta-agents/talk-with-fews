import os
import pytest
import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.utils_tests import setup_dot_env
from talk_with_fews.routers.setup_connections import (
    get_runtime_ctx,
    _cache_manager,
)


@pytest.fixture(autouse=True)
def clear_cached_configs():
    """Clear the global cached configs before each test."""
    _cache_manager.clear()
    yield
    _cache_manager.clear()


@pytest.fixture
def user_settings():
    """Provide basic user settings for testing."""
    return setup_dot_env()


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_basic(user_settings):
    """Test basic context creation."""
    ctx = get_runtime_ctx(user_settings)

    assert ctx.deps is not None
    assert ctx.deps.db_path == user_settings["FEWS_DB_PATH"]
    assert ctx.deps.webservice_url == user_settings["FEWS_WEB_SERVICE_URL"]
    assert ctx.deps.schema is not None
    assert ctx.deps.db_connection is not None


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_caching(user_settings):
    """Test that subsequent calls use cached values."""
    # First call
    ctx1 = get_runtime_ctx(user_settings)

    # Second call with same client_id
    ctx2 = get_runtime_ctx(user_settings)

    # Should reuse cached connection
    assert ctx1.deps.db_connection is ctx2.deps.db_connection
    assert ctx1.deps.schema is ctx2.deps.schema


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_different_users():
    """Test that different users get separate contexts."""
    base_settings = setup_dot_env()

    user1_settings = base_settings.copy()
    user1_settings["client_id"] = "user1"
    user1_settings["FEWS_WEB_SERVICE_URL"] = None

    user2_settings = base_settings.copy()
    user2_settings["client_id"] = "user2"
    user2_settings["FEWS_WEB_SERVICE_URL"] = None

    ctx1 = get_runtime_ctx(user1_settings)
    ctx2 = get_runtime_ctx(user2_settings)

    # Different users should have separate connections
    assert ctx1.deps.db_connection is not ctx2.deps.db_connection


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_webservice_db_always_exists(user_settings):
    """Test that cache_FewsWebServices_db is never None when webservice URL is provided."""
    # Even with DEV_DISABLE_WEBSERVICE_INGEST=true, the DB connection should exist
    ctx = get_runtime_ctx(user_settings)

    if user_settings["FEWS_WEB_SERVICE_URL"] is not None:
        # DB connection should always exist (not None) so tools can call .execute()
        assert ctx.deps.cache_FewsWebServices_db is not None, (
            "cache_FewsWebServices_db should never be None when webservice URL is provided"
        )
        # Verify it's a valid DuckDB connection
        result = ctx.deps.cache_FewsWebServices_db.execute("SELECT 1").fetchone()
        assert result == (1,), "DuckDB connection should be functional"


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_with_ingestion_disabled():
    """Test that when DEV_DISABLE_WEBSERVICE_INGEST=true, DB exists but no data is ingested."""
    os.environ["DEV_DISABLE_WEBSERVICE_INGEST"] = "true"

    try:
        user_settings = setup_dot_env()
        user_settings["client_id"] = "test-ingestion-disabled"

        ctx = get_runtime_ctx(user_settings)

        if user_settings["FEWS_WEB_SERVICE_URL"] is not None:
            # DB connection should exist
            assert ctx.deps.cache_FewsWebServices_db is not None

            # But tables should NOT exist (no ingestion happened)
            # Check that locations table does not exist
            try:
                ctx.deps.cache_FewsWebServices_db.execute(
                    "SELECT COUNT(*) FROM locations"
                ).fetchone()
                assert False, (
                    "locations table should not exist when ingestion is disabled"
                )
            except Exception as e:
                # Expected - table doesn't exist
                assert "does not exist" in str(e)

            # Ingestion outputs are no longer stored in Deps model
    finally:
        os.environ.pop("DEV_DISABLE_WEBSERVICE_INGEST", None)


@pytest.mark.skipif(
    os.getenv("DEV_SKIP_SETUP_CONNECTIONS_TESTS", "false") == "true",
    reason="Skipping setup_connections tests",
)
def test_get_runtime_ctx_with_ingestion_enabled():
    """Test that when DEV_DISABLE_WEBSERVICE_INGEST=false, DB exists with data ingested."""
    # Clear the cache first to ensure fresh state
    _cache_manager.clear()

    os.environ["DEV_DISABLE_WEBSERVICE_INGEST"] = "false"

    try:
        user_settings = setup_dot_env()
        user_settings["client_id"] = "test-ingestion-enabled"

        ctx = get_runtime_ctx(user_settings)

        if user_settings["FEWS_WEB_SERVICE_URL"] is not None:
            # DB connection should exist
            assert ctx.deps.cache_FewsWebServices_db is not None

            # Tables SHOULD exist (ingestion happened)
            locations_count = ctx.deps.cache_FewsWebServices_db.execute(
                "SELECT COUNT(*) FROM locations"
            ).fetchone()[0]
            assert locations_count > 0, "locations table should have data"

            parameters_count = ctx.deps.cache_FewsWebServices_db.execute(
                "SELECT COUNT(*) FROM parameters"
            ).fetchone()[0]
            assert parameters_count > 0, "parameters table should have data"

            # series_headers table should exist (even if empty)
            series_headers_count = ctx.deps.cache_FewsWebServices_db.execute(
                "SELECT COUNT(*) FROM series_headers"
            ).fetchone()[0]
            assert series_headers_count >= 0, "series_headers table should exist"

            # Verify that ingestion actually happened by checking the data exists
            # (the ingestion output objects might not be cached, but data should be there)
    finally:
        os.environ.pop("DEV_DISABLE_WEBSERVICE_INGEST", None)
