import os
from pathlib import Path
from dotenv import load_dotenv
from tests.test_config import get_test_service_config, generate_test_client_id


def setup_dot_env():
    """
    Setup environment and return user settings for testing.

    This function ensures that webservice ingestion is enabled by default for tests,
    which is required by most webservice-related tests (test_get_locations,
    test_get_parameters, test_get_series_headers, etc.)

    Note: Individual tests can override DEV_DISABLE_WEBSERVICE_INGEST if needed.

    The FEWS service configuration is determined by:
    - FEWS_TEST_SERVICE environment variable (for local testing)
    - CI environment detection (defaults to actueelwaterbeeld in CI)
    - Default to actueelwaterbeeld
    """
    env_template = Path(__file__).parent.parent / "env" / ".env.example"
    env_copy = Path(__file__).parent.parent / "env" / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path="env/.env")

    # Ensure webservice ingestion is enabled for tests (unless explicitly disabled)
    # This is necessary because many tests expect the locations/parameters tables to exist
    if "DEV_DISABLE_WEBSERVICE_INGEST" not in os.environ:
        os.environ["DEV_DISABLE_WEBSERVICE_INGEST"] = "false"

    # Get the appropriate FEWS service configuration
    service_config = get_test_service_config()

    return {
        "client_id": generate_test_client_id(),
        "FEWS_DB_PATH": service_config.db_path,
        "FEWS_WEB_SERVICE_URL": service_config.web_service_url,
        "scopes": ["read:data"],
    }
