#!/usr/bin/env python3

import argparse
import logging
import time
from rpi_rf import RFDevice

# Configuration
GPIO_PIN = 17
DEFAULT_PULSE = 189

# Outlet Codes (from controller.py)
OUTLETS = {
    1: {"on": 1332531, "off": 1332540},
    2: {"on": 1332675, "off": 1332684},
    3: {"on": 1332995, "off": 1333004},
    4: {"on": 1334531, "off": 1334540},
    5: {"on": 1340675, "off": 1340684},
}

def sweep(outlet_id, state, gpio=GPIO_PIN):
    if outlet_id not in OUTLETS:
        print(f"Invalid outlet ID: {outlet_id}")
        return

    code = OUTLETS[outlet_id][state]
    rfdevice = RFDevice(gpio)
    rfdevice.enable_tx()

    print(f"Sweeping pulse lengths for Outlet {outlet_id} ({state}) - Code: {code}")
    print("Press CTRL+C to stop.")

    # Range of pulse lengths to try (Standard is often 170-210)
    # We will try a wider range just in case.
    pulse_range = range(150, 250, 2) 
    
    try:
        for protocol in [1, 2, 3, 4, 5]:
            print(f"\n--- Testing Protocol {protocol} ---")
            for pulse in pulse_range:
                print(f"Sending: Protocol={protocol}, Pulse={pulse}...", end='\r')
                rfdevice.tx_code(code, protocol, pulse)
                time.sleep(0.05) # Small delay between sends
    except KeyboardInterrupt:
        print("\nSweep stopped.")
    finally:
        rfdevice.cleanup()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sweep pulse lengths to find working configuration')
    parser.add_argument('outlet', type=int, help="Outlet ID (1-5)")
    parser.add_argument('state', type=str, help="State (on/off)")
    args = parser.parse_args()

    sweep(args.outlet, args.state)
