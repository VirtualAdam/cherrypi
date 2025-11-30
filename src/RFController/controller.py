#!/usr/bin/env python3

import argparse
import logging
import time
from rpi_rf import RFDevice

# Configuration
GPIO_PIN = 17
PULSE_LENGTH = 189
PROTOCOL = 1

# Outlet Codes
OUTLETS = {
    1: {"on": 1332531, "off": 1332540},
    2: {"on": 1332675, "off": 1332684},
    3: {"on": 1332995, "off": 1333004},
    4: {"on": 1334531, "off": 1334540},
    5: {"on": 1340675, "off": 1340684},
}

def send_code(code, gpio=GPIO_PIN, pulselength=PULSE_LENGTH, protocol=PROTOCOL):
    rfdevice = RFDevice(gpio)
    rfdevice.enable_tx()
    rfdevice.tx_code(code, protocol, pulselength)
    rfdevice.cleanup()
    logging.info(f"Sent code: {code}")

def control_outlet(outlet_id, state):
    if outlet_id not in OUTLETS:
        logging.error(f"Invalid outlet ID: {outlet_id}")
        return

    if state.lower() not in ['on', 'off']:
        logging.error("State must be 'on' or 'off'")
        return

    code = OUTLETS[outlet_id][state.lower()]
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
