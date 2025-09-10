from fastapi.testclient import TestClient
from src.main import app
from tests.utils_tests import setup_dot_env
import pytest


def test_get_database_schema():
    _ = setup_dot_env()
    client = TestClient(app)
    with pytest.warns(UserWarning):
        response = client.post(
            "/tools.config/get_database_schema",
            headers={"Authorization": "Bearer example-token"},
            json={},
        )

    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert "tables" in response.json()
    assert "relationships" in response.json()
    assert "sample_data" in response.json()
