import os
from pathlib import Path
from dotenv import load_dotenv


def setup_dot_env():
    """
    Setup environment and return user settings for testing.

    This function ensures that webservice ingestion is enabled by default for tests,
    which is required by most webservice-related tests (test_get_locations,
    test_get_parameters, test_get_series_headers, etc.)

    Note: Individual tests can override DEV_DISABLE_WEBSERVICE_INGEST if needed.
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

    return {
        "client_id": "example",
        "FEWS_DB_PATH": "data/fews_config.db3",
        "FEWS_WEB_SERVICE_URL": "https://actueelwaterbeeld-api.hkvservices.nl/FewsWebServices",
        # "FEWS_DB_PATH": "data/HDSR_wis.db3",
        # "FEWS_WEB_SERVICE_URL": "http://talk-with-fews.hkvservices.nl:8080/FewsWebServicesHDSR",
        "scopes": ["read:data"],
    }
