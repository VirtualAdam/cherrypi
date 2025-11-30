import sys
import os
from unittest.mock import MagicMock, patch

# Conditionally mock rpi_rf and RPi.GPIO if they are not available
try:
    import rpi_rf
    import RPi.GPIO
except ImportError:
    sys.modules['rpi_rf'] = MagicMock()
    sys.modules['RPi.GPIO'] = MagicMock()

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from RFController.controller import control_outlet, OUTLETS

def test_outlet_codes_exist():
    assert 1 in OUTLETS
    assert "on" in OUTLETS[1]
    assert "off" in OUTLETS[1]

@patch('RFController.controller.send_code')
def test_control_outlet_logic(mock_send_code):
    control_outlet(1, "on")
    expected_code = OUTLETS[1]["on"]
    mock_send_code.assert_called_with(expected_code)

@patch('RFController.controller.send_code')
def test_control_outlet_off(mock_send_code):
    control_outlet(2, "off")
    expected_code = OUTLETS[2]["off"]
    mock_send_code.assert_called_with(expected_code)
