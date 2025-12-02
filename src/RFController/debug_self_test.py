#!/usr/bin/env python3
"""
Self-test: Transmit and receive on the same Pi
This confirms if the receiver module can detect signals at all.
"""

import time
import threading
import sys

try:
    from rpi_rf import RFDevice
except ImportError:
    print("ERROR: rpi_rf not installed. Run: pip install rpi-rf")
    sys.exit(1)

TX_PIN = 17
RX_PIN = 27
TEST_CODE = 1332531  # Known working code from config
PULSE_LENGTH = 189
PROTOCOL = 1

print("=" * 60)
print("RF Self-Test: Transmit and Receive")
print("=" * 60)
print()
print(f"Transmitter: GPIO {TX_PIN}")
print(f"Receiver: GPIO {RX_PIN}")
print(f"Test code: {TEST_CODE}")
print(f"Pulse length: {PULSE_LENGTH}µs")
print(f"Protocol: {PROTOCOL}")
print()

# Results storage
received_codes = []

def receiver_thread():
    """Listen for signals"""
    rx = RFDevice(RX_PIN)
    rx.enable_rx()
    
    start_time = time.time()
    while time.time() - start_time < 10:  # Listen for 10 seconds
        if rx.rx_code_timestamp:
            code = rx.rx_code
            pulse = rx.rx_pulselength
            proto = rx.rx_proto
            if code and code not in [c[0] for c in received_codes[-3:]]:
                received_codes.append((code, pulse, proto, time.time()))
                print(f"  📡 RECEIVED: Code={code}, Pulse={pulse}µs, Protocol={proto}")
            rx.rx_code_timestamp = 0
        time.sleep(0.01)
    
    rx.cleanup()

def transmitter_thread():
    """Transmit test signals"""
    time.sleep(1)  # Give receiver time to start
    
    tx = RFDevice(TX_PIN)
    tx.enable_tx()
    tx.tx_proto = PROTOCOL
    tx.tx_pulselength = PULSE_LENGTH
    
    print("\n📤 Transmitting test signals...")
    
    for i in range(5):
        print(f"  Sending code {TEST_CODE}...")
        tx.tx_code(TEST_CODE, PROTOCOL, PULSE_LENGTH, 3)  # 3 repeats
        time.sleep(1)
    
    tx.cleanup()
    print("📤 Transmission complete")

# Start both threads
print("Starting self-test (10 seconds)...")
print()

rx_thread = threading.Thread(target=receiver_thread)
tx_thread = threading.Thread(target=transmitter_thread)

rx_thread.start()
tx_thread.start()

rx_thread.join()
tx_thread.join()

# Results
print()
print("=" * 60)
print("RESULTS")
print("=" * 60)

if received_codes:
    print(f"\n✅ SUCCESS! Received {len(received_codes)} signals!")
    print("\nReceived codes:")
    for code, pulse, proto, ts in received_codes:
        match = "✓ MATCH!" if code == TEST_CODE else ""
        print(f"  Code: {code}, Pulse: {pulse}µs, Protocol: {proto} {match}")
    
    print("\n🎉 The receiver module is working!")
    print("   The issue is the high noise floor drowning out your remote.")
    print("\n   Recommendations:")
    print("   1. Move receiver further from Pi (longer wires)")
    print("   2. Add a 0.1µF capacitor between VCC and GND on receiver")
    print("   3. Use 3.3V instead of 5V for the receiver")
    print("   4. Adjust the tuning coil on the receiver")
else:
    print("\n❌ No signals received from self-test!")
    print("\n   This means the receiver module may be faulty or")
    print("   the noise is completely overwhelming the receiver.")
    print("\n   Try:")
    print("   1. Power receiver from 3.3V instead of 5V")
    print("   2. The receiver module might be defective")
