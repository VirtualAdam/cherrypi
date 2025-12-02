#!/usr/bin/env python3

import argparse
import logging
import time
from rpi_rf import RFDevice
from config_manager import get_outlets_dict, get_settings, load_config

# Load configuration from config.json
def get_config():
    """Load settings from config"""
    settings = get_settings()
    return {
        'gpio_pin': settings.get('gpio_tx_pin', 17),
        'pulse_length': settings.get('pulse_length', 189),
        'protocol': settings.get('protocol', 1)
    }

def get_outlets():
    """Load outlets from config"""
    return get_outlets_dict()

def send_code(code, gpio=None, pulselength=None, protocol=None):
    config = get_config()
    gpio = gpio or config['gpio_pin']
    pulselength = pulselength or config['pulse_length']
    protocol = protocol or config['protocol']
    
    rfdevice = RFDevice(gpio)
    rfdevice.enable_tx()
    rfdevice.tx_code(code, protocol, pulselength)
    rfdevice.cleanup()
    logging.info(f"Sent code: {code}")

def control_outlet(outlet_id, state):
    outlets = get_outlets()
    
    if outlet_id not in outlets:
        logging.error(f"Invalid outlet ID: {outlet_id}")
        return

    if state.lower() not in ['on', 'off']:
        logging.error("State must be 'on' or 'off'")
        return

    code = outlets[outlet_id][state.lower()]
    logging.info(f"Turning Outlet {outlet_id} {state.upper()}...")
    send_code(code)

def main():
    parser = argparse.ArgumentParser(description='Control RF Outlets')
    parser.add_argument('outlet', type=int, help="Outlet ID (1-5)")
    parser.add_argument('state', type=str, help="State (on/off)")
    args = parser.parse_args()

    control_outlet(args.outlet, args.state)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    main()
