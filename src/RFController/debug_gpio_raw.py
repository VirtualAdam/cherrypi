#!/usr/bin/env python3
"""
Low-level GPIO debug - filters noise and detects actual RF signal bursts
Looks for patterns that indicate real RF transmission vs background noise
"""

import time
import RPi.GPIO as GPIO

GPIO_PIN = 27  # Physical Pin 13

# Signal detection parameters
BURST_THRESHOLD = 50      # Min transitions to consider a "burst"
QUIET_PERIOD = 0.1        # Seconds of quiet to end a burst
MIN_BURST_DURATION = 0.05 # Minimum burst length in seconds

print("=" * 60)
print("RF Signal Burst Detector (Noise Filtered)")
print("=" * 60)
print(f"Monitoring GPIO {GPIO_PIN}")
print()
print("This script detects BURSTS of activity that indicate")
print("a real RF transmission vs random background noise.")
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN)

print("Measuring background noise for 2 seconds...")
noise_count = 0
noise_start = time.time()
last_state = GPIO.input(GPIO_PIN)

while time.time() - noise_start < 2.0:
    current_state = GPIO.input(GPIO_PIN)
    if current_state != last_state:
        noise_count += 1
        last_state = current_state
    time.sleep(0.00005)

noise_rate = noise_count / 2.0
print(f"Background noise: ~{noise_rate:.0f} transitions/sec")

if noise_rate > 1000:
    print()
    print("⚠️  HIGH NOISE LEVEL DETECTED!")
    print("   This is common with these receivers. Solutions:")
    print("   1. Add a 17.3cm antenna wire to the ANT pad")
    print("   2. Add 0.1uF capacitor between VCC and GND")
    print("   3. Move receiver away from Pi/power supply")
    print()

print()
print("Now press buttons on your remote...")
print("Looking for signal BURSTS (different from constant noise)")
print("Press Ctrl+C to stop")
print("-" * 60)

# Track bursts of activity
burst_transitions = []
burst_start = None
last_activity = time.time()
last_state = GPIO.input(GPIO_PIN)
bursts_detected = 0

try:
    while True:
        current_state = GPIO.input(GPIO_PIN)
        now = time.time()
        
        if current_state != last_state:
            # Activity detected
            if burst_start is None:
                burst_start = now
                burst_transitions = []
            
            burst_transitions.append(now - burst_start)
            last_activity = now
            last_state = current_state
        
        # Check if burst ended (quiet period)
        if burst_start is not None and (now - last_activity) > QUIET_PERIOD:
            burst_duration = last_activity - burst_start
            transition_count = len(burst_transitions)
            
            # Filter: real RF signals have specific characteristics
            # - Many transitions in a short burst
            # - Then quiet (signal ends)
            if transition_count > BURST_THRESHOLD and burst_duration > MIN_BURST_DURATION:
                bursts_detected += 1
                rate = transition_count / burst_duration if burst_duration > 0 else 0
                print(f"\n🔔 BURST #{bursts_detected} DETECTED!")
                print(f"   Duration: {burst_duration*1000:.1f}ms")
                print(f"   Transitions: {transition_count}")
                print(f"   Rate: {rate:.0f}/sec")
                
                # Try to estimate if this looks like a real signal
                if 100 < burst_duration * 1000 < 2000 and transition_count > 100:
                    print(f"   ✓ This looks like a real RF signal!")
                else:
                    print(f"   ? Unusual pattern - might be interference")
            
            burst_start = None
            burst_transitions = []
        
        time.sleep(0.00005)  # 50µs polling for better resolution

except KeyboardInterrupt:
    print()
    print("=" * 60)
    print(f"Total signal bursts detected: {bursts_detected}")
    
    if bursts_detected == 0:
        print()
        print("No clear RF bursts detected above the noise.")
        print()
        print("Suggestions:")
        print("  1. Add an antenna - solder 17.3cm wire to ANT pad")
        print("  2. Hold remote VERY close to receiver (< 5cm)")
        print("  3. Check if remote has a working battery")
        print("  4. Verify remote is 433MHz (not 315MHz or other)")
    else:
        print()
        print("✓ RF signals detected!")
        print("  The receiver is working but rpi_rf may need tuning.")
    print("=" * 60)

finally:
    GPIO.cleanup()
