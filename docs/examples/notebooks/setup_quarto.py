import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import subprocess

logger = logging.getLogger("fews_agent")
logger.setLevel(logging.WARNING)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


def setup_dot_env_docs(download_schemas: bool = False):
    logger.info("Setting up .env file")
    work_dir = Path(__file__).parent.parent.parent.parent
    env_path = work_dir / "env"
    env_template = env_path / ".env.example"
    env_copy = env_path / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path=env_copy)
    user_settings = {
        "client_id": "example",
        "FEWS_DB_PATH": "data/fews_config.db3",
        "FEWS_WEB_SERVICE_URL": "https://data.hkvfewsscheldestromen.nl:8443/FewsWebServices/",
        "scopes": ["read:data"],
    }
    os.chdir(work_dir)
    # talk_with_fews loads env/ from the working directory when it is imported,
    # so import it only after switching to the repo root.
    from talk_with_fews.routers.setup_connections import get_runtime_ctx

    ctx = get_runtime_ctx(user_settings)
    if download_schemas:
        subprocess.run(["pixi", "run", "download-schemas"], check=True)
    return ctx
