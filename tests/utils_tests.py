from pathlib import Path
from dotenv import load_dotenv


def setup_dot_env():
    env_template = Path(__file__).parent.parent / "env" / ".env.example"
    env_copy = Path(__file__).parent.parent / "env" / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path="env/.env")
