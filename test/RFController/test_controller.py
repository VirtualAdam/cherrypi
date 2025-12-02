import sys
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

# Add RFController to path for relative imports within that module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/RFController')))

# Conditionally mock rpi_rf, RPi.GPIO, and custom_rf_decoder if they are not available
try:
    import rpi_rf
    import RPi.GPIO
except ImportError:
    sys.modules['rpi_rf'] = MagicMock()
    sys.modules['RPi.GPIO'] = MagicMock()

# Mock custom_rf_decoder for tests
mock_decoder = MagicMock()
sys.modules['custom_rf_decoder'] = mock_decoder

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))


# --- Test config_manager ---

def test_config_manager_get_outlets_dict():
    """Test that config_manager can convert switches to outlets dict"""
    from RFController import config_manager
    
    # Mock the load_config to return test data
    test_config = {
        "switches": [
            {"id": 1, "name": "Test 1", "on_code": 111, "off_code": 112},
            {"id": 2, "name": "Test 2", "on_code": 221, "off_code": 222}
        ],
        "settings": {}
    }
    
    with patch.object(config_manager, 'load_config', return_value=test_config):
        outlets = config_manager.get_outlets_dict()
        
        assert 1 in outlets
        assert 2 in outlets
        assert outlets[1]["on"] == 111
        assert outlets[1]["off"] == 112
        assert outlets[2]["on"] == 221
        assert outlets[2]["off"] == 222


def test_config_manager_get_next_id():
    """Test auto-increment ID generation"""
    from RFController import config_manager
    
    test_config = {
        "switches": [
            {"id": 1, "name": "Test 1", "on_code": 111, "off_code": 112},
            {"id": 5, "name": "Test 5", "on_code": 551, "off_code": 552}
        ],
        "settings": {}
    }
    
    with patch.object(config_manager, 'load_config', return_value=test_config):
        next_id = config_manager.get_next_id()
        assert next_id == 6  # Should be max(1, 5) + 1


def test_config_manager_get_next_id_empty():
    """Test ID generation with no switches"""
    from RFController import config_manager
    
    test_config = {"switches": [], "settings": {}}
    
    with patch.object(config_manager, 'load_config', return_value=test_config):
        next_id = config_manager.get_next_id()
        assert next_id == 1


# --- Test controller ---

def test_control_outlet_on():
    """Test turning an outlet on"""
    from RFController import controller
    
    with patch.object(controller, 'get_outlets', return_value={1: {"on": 12345, "off": 12346}}):
        with patch.object(controller, 'send_code') as mock_send_code:
            controller.control_outlet(1, "on")
            mock_send_code.assert_called_with(12345)


def test_control_outlet_off():
    """Test turning an outlet off"""
    from RFController import controller
    
    with patch.object(controller, 'get_outlets', return_value={1: {"on": 12345, "off": 12346}}):
        with patch.object(controller, 'send_code') as mock_send_code:
            controller.control_outlet(1, "off")
            mock_send_code.assert_called_with(12346)


def test_control_outlet_invalid_id():
    """Test with invalid outlet ID - should not send code"""
    from RFController import controller
    
    with patch.object(controller, 'get_outlets', return_value={1: {"on": 12345, "off": 12346}}):
        with patch.object(controller, 'send_code') as mock_send_code:
            controller.control_outlet(99, "on")  # ID 99 doesn't exist
            mock_send_code.assert_not_called()


def test_control_outlet_invalid_state():
    """Test with invalid state - should not send code"""
    from RFController import controller
    
    with patch.object(controller, 'get_outlets', return_value={1: {"on": 12345, "off": 12346}}):
        with patch.object(controller, 'send_code') as mock_send_code:
            controller.control_outlet(1, "invalid")
            mock_send_code.assert_not_called()
