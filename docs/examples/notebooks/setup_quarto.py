import os
from pathlib import Path
from dotenv import load_dotenv
from talk_with_fews.routers.setup_connections import get_runtime_ctx
import logging
from ....scripts.download_fews_schemas import download_fews_schemas

logger = logging.getLogger("fews_agent")
logger.setLevel(logging.WARNING)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


def setup_dot_env():
    logger.info("Setting up .env file")
    work_dir = Path(__file__).parent.parent.parent.parent
    env_path = work_dir / "env"
    env_template = env_path / ".env.example"
    env_copy = env_path / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path=env_copy)

    os.chdir(work_dir)
    ctx = get_runtime_ctx()
    download_fews_schemas()
    return ctx
