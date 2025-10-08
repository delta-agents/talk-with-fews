import pytest
import sys
from pathlib import Path

# Add src and tests to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.utils_tests import setup_dot_env
from talk_with_fews.routers.setup_connections import (
    get_runtime_ctx,
    _cached_configs,
)


@pytest.fixture(autouse=True)
def clear_cached_configs():
    """Clear the global cached configs before each test."""
    _cached_configs.clear()
    yield
    _cached_configs.clear()


@pytest.fixture
def user_settings():
    """Provide basic user settings for testing."""
    return setup_dot_env()


def test_get_runtime_ctx_basic(user_settings):
    """Test basic context creation."""
    ctx = get_runtime_ctx(user_settings)

    assert ctx.deps is not None
    assert ctx.deps.db_path == user_settings["FEWS_DB_PATH"]
    assert ctx.deps.webservice_url == user_settings["FEWS_WEB_SERVICE_URL"]
    assert ctx.deps.schema is not None
    assert ctx.deps.db_connection is not None


def test_get_runtime_ctx_caching(user_settings):
    """Test that subsequent calls use cached values."""
    # First call
    ctx1 = get_runtime_ctx(user_settings)

    # Second call with same client_id
    ctx2 = get_runtime_ctx(user_settings)

    # Should reuse cached connection
    assert ctx1.deps.db_connection is ctx2.deps.db_connection
    assert ctx1.deps.schema is ctx2.deps.schema


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
