from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os
import json

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
    # Mock Redis to return a valid switch config
    mock_redis.get.return_value = json.dumps([
        {"id": 1, "name": "Test Switch", "on_code": 123, "off_code": 456}
    ])
    
    response = client.post("/api/outlet", json={"outlet_id": 1, "state": "on"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_redis.publish.assert_called_once()


def test_control_outlet_invalid_state():
    response = client.post("/api/outlet", json={"outlet_id": 1, "state": "invalid"})
    assert response.status_code == 400


@patch('backend.main.r')
def test_control_outlet_invalid_id(mock_redis):
    # Mock Redis to return config with only switch ID 1
    mock_redis.get.return_value = json.dumps([
        {"id": 1, "name": "Test Switch", "on_code": 123, "off_code": 456}
    ])
    
    # Try to control switch ID 99 which doesn't exist
    response = client.post("/api/outlet", json={"outlet_id": 99, "state": "on"})
    assert response.status_code == 400
    assert "Invalid outlet ID" in response.json()["detail"]


@patch('backend.main.r')
def test_control_outlet_redis_error(mock_redis):
    # Mock config lookup to succeed
    mock_redis.get.return_value = json.dumps([
        {"id": 1, "name": "Test Switch", "on_code": 123, "off_code": 456}
    ])
    # Simulate Redis connection error during publish
    mock_redis.publish.side_effect = Exception("Connection lost")
    
    response = client.post("/api/outlet", json={"outlet_id": 1, "state": "on"})
    assert response.status_code == 500
    assert "Redis Error" in response.json()["detail"]


# --- New tests for switch management ---

@patch('backend.main.r')
def test_get_switches_from_redis(mock_redis):
    """Test getting switches from Redis cache"""
    mock_switches = [
        {"id": 1, "name": "Living Room", "on_code": 111, "off_code": 112},
        {"id": 2, "name": "Bedroom", "on_code": 221, "off_code": 222}
    ]
    mock_redis.get.return_value = json.dumps(mock_switches)
    
    response = client.get("/api/switches")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "Living Room"


@patch('backend.main.r')
def test_get_switches_empty(mock_redis):
    """Test getting switches when none exist"""
    mock_redis.get.return_value = None
    
    response = client.get("/api/switches")
    assert response.status_code == 200
    assert response.json() == []


@patch('backend.main.r')
def test_get_sniffer_status(mock_redis):
    """Test getting sniffer status"""
    mock_redis.get.return_value = json.dumps({"active": False})
    
    response = client.get("/api/sniffer/status")
    assert response.status_code == 200
    assert response.json()["active"] == False
