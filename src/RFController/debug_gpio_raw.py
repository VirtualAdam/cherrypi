#!/usr/bin/env python3
"""
Low-level GPIO debug - checks for ANY signal changes on the pin
This bypasses rpi_rf to see raw GPIO state changes
"""

import time
import RPi.GPIO as GPIO

GPIO_PIN = 27  # Physical Pin 13

print("=" * 50)
print("Low-Level GPIO Signal Detector")
print("=" * 50)
print(f"Monitoring GPIO {GPIO_PIN} for ANY state changes")
print("This will detect if the receiver is sending anything at all")
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN)

print("Press buttons on your remote...")
print("You should see HIGH/LOW changes if receiver is working")
print("Press Ctrl+C to stop")
print()

last_state = GPIO.input(GPIO_PIN)
change_count = 0
start_time = time.time()

print(f"Initial state: {'HIGH' if last_state else 'LOW'}")
print()

try:
    while True:
        current_state = GPIO.input(GPIO_PIN)
        
        if current_state != last_state:
            change_count += 1
            elapsed = time.time() - start_time
            state_str = 'HIGH' if current_state else 'LOW'
            
            # Only print first 50 changes to avoid spam
            if change_count <= 50:
                print(f"[{elapsed:.3f}s] Change #{change_count}: -> {state_str}")
            elif change_count == 51:
                print("... (more changes detected, stopping print to avoid spam)")
            
            last_state = current_state
        
        time.sleep(0.0001)  # 0.1ms polling

except KeyboardInterrupt:
    print()
    print("=" * 50)
    elapsed = time.time() - start_time
    print(f"Monitoring time: {elapsed:.1f} seconds")
    print(f"Total state changes detected: {change_count}")
    
    if change_count == 0:
        print()
        print("⚠️  NO SIGNALS DETECTED!")
        print()
        print("Possible causes:")
        print("  1. Check wiring - is DATA wire on GPIO 27 (Pin 13)?")
        print("  2. Check power - is VCC getting 5V?")
        print("  3. Remote might be different frequency (not 433MHz)")
        print("  4. Try adjusting the potentiometer on the receiver")
        print("  5. Try moving remote closer to receiver")
    else:
        print()
        print("✓ Signals detected! The receiver is working.")
        print("  If rpi_rf didn't decode them, try adjusting the")
        print("  potentiometer on the receiver module for cleaner signal.")
    print("=" * 50)

finally:
    GPIO.cleanup()
