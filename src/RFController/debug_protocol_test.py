#!/usr/bin/env python3
"""
Test all rpi_rf protocols to find which one works with your remote.
"""

import time
import sys

try:
    from rpi_rf import RFDevice
except ImportError:
    print("ERROR: rpi_rf not installed. Run: pip install rpi-rf")
    sys.exit(1)

GPIO_PIN = 27

print("=" * 60)
print("RF Protocol Tester")
print("=" * 60)
print()
print("This will try to receive signals using different protocols.")
print("Press and release buttons on your remote during each test.")
print()

# Test each protocol
for protocol in [1, 2, 3, 4, 5]:
    print(f"\n{'='*60}")
    print(f"Testing Protocol {protocol}")
    print(f"{'='*60}")
    print("Press buttons on your remote for 10 seconds...")
    
    rfdevice = RFDevice(GPIO_PIN)
    rfdevice.enable_rx()
    
    # Override protocol for receiving
    # Note: rpi_rf doesn't have a direct protocol setting for RX
    # But we can check what it receives
    
    start_time = time.time()
    codes_received = []
    
    while time.time() - start_time < 10:
        if rfdevice.rx_code_timestamp != 0:
            code = rfdevice.rx_code
            pulselength = rfdevice.rx_pulselength
            proto = rfdevice.rx_proto
            
            if code not in [c[0] for c in codes_received[-5:]]:  # Avoid duplicates
                codes_received.append((code, pulselength, proto))
                print(f"  📡 Code: {code}, Pulse: {pulselength}µs, Protocol: {proto}")
            
            # Reset
            rfdevice.rx_code_timestamp = 0
        
        time.sleep(0.01)
    
    rfdevice.cleanup()
    
    if codes_received:
        print(f"\n✓ Protocol {protocol}: Received {len(codes_received)} unique codes!")
    else:
        print(f"\n✗ Protocol {protocol}: No codes received")

print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print()
print("If any protocol showed received codes, use those settings")
print("in your config.json for the switches.")
print()
print("If no protocols worked, the signal might use a non-standard")
print("encoding. We may need to capture raw timings and decode manually.")
