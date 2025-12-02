#!/usr/bin/env python3
"""
Debug script for testing 433MHz RF Receiver
Run directly on the Pi: python3 debug_receiver.py

Wiring (your setup):
  - Green wire (DATA) → Pi Pin 13 (GPIO 27)
  - Yellow wire (VCC) → Pi Pin 4 (5V)
  - Blue wire (GND) → Pi Pin 9 (Ground)
"""

import time
import sys

# Configuration
GPIO_PIN = 27  # GPIO 27 = Physical Pin 13

print("=" * 50)
print("433MHz RF Receiver Debug Tool")
print("=" * 50)
print(f"Listening on GPIO {GPIO_PIN} (Physical Pin 13)")
print()

# Try to import rpi_rf
try:
    from rpi_rf import RFDevice
    print("✓ rpi_rf library loaded successfully")
except ImportError as e:
    print(f"✗ Failed to import rpi_rf: {e}")
    print("\nInstall with: pip install rpi-rf")
    sys.exit(1)

# Try to initialize the receiver
try:
    rfdevice = RFDevice(GPIO_PIN)
    rfdevice.enable_rx()
    print("✓ RF Receiver initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize RF device: {e}")
    sys.exit(1)

print()
print("=" * 50)
print("LISTENING FOR RF SIGNALS...")
print("Press buttons on your 433MHz remote control")
print("Press Ctrl+C to stop")
print("=" * 50)
print()

timestamp = None
signal_count = 0

try:
    while True:
        if rfdevice.rx_code_timestamp != timestamp:
            timestamp = rfdevice.rx_code_timestamp
            signal_count += 1
            
            code = rfdevice.rx_code
            pulselength = rfdevice.rx_pulselength
            protocol = rfdevice.rx_proto
            
            print(f"[{signal_count}] Received signal!")
            print(f"    Code:        {code}")
            print(f"    Pulselength: {pulselength}")
            print(f"    Protocol:    {protocol}")
            print()
            
        time.sleep(0.01)
        
except KeyboardInterrupt:
    print()
    print("=" * 50)
    print(f"Stopped. Total signals received: {signal_count}")
    print("=" * 50)
    
finally:
    rfdevice.cleanup()
    print("GPIO cleaned up.")
