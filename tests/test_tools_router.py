import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from fastapi.testclient import TestClient
from src.main import app
from pathlib import Path
from dotenv import load_dotenv


def setup_dot_env():
    env_template = Path(__file__).parent.parent / "env" / ".env.example"
    env_copy = Path(__file__).parent.parent / "env" / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path="env/.env")


def test_get_database_schema():
    setup_dot_env()
    client = TestClient(app)
    response = client.post("/tools/get_database_schema", json={})
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert "tables" in response.json()
    assert "relationships" in response.json()
    assert "sample_data" in response.json()
