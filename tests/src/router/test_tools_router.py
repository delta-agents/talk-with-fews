from fastapi.testclient import TestClient
from src.main import app
import pytest


def test_get_database_schema():
    client = TestClient(app)

    try:
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
    finally:
        # Clean up any database connections that might have been created
        # The TestClient should handle this, but let's be explicit
        pass
