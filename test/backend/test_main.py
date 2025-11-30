from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path so we can import backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch('backend.main.r')
def test_control_outlet_valid(mock_redis):
    response = client.post("/api/outlet", json={"outlet_id": 4, "state": "on"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_redis.publish.assert_called_once()

def test_control_outlet_invalid_state():
    response = client.post("/api/outlet", json={"outlet_id": 4, "state": "invalid"})
    assert response.status_code == 400

def test_control_outlet_invalid_id():
    response = client.post("/api/outlet", json={"outlet_id": 99, "state": "on"})
    assert response.status_code == 400

@patch('backend.main.r')
def test_control_outlet_redis_error(mock_redis):
    # Simulate Redis connection error during publish
    mock_redis.publish.side_effect = Exception("Connection lost")
    
    response = client.post("/api/outlet", json={"outlet_id": 1, "state": "on"})
    assert response.status_code == 500
    assert "Redis Error" in response.json()["detail"]
