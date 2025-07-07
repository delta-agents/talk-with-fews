import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fastapi.testclient import TestClient
from src.main import app

def test_get_database_schema():
    client = TestClient(app)
    response = client.post("/tools/get_database_schema", json={})
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
    assert response.status_code == 200
    assert "tables" in response.json()
    assert "relationships" in response.json()
    assert "sample_data" in response.json() 