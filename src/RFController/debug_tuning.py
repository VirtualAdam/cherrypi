#!/usr/bin/env python3
"""
Tuning Coil Calibration Tool
Helps find the optimal receiver tuning by testing after each adjustment.
"""

import time
import RPi.GPIO as GPIO

RX_PIN = 27

print("=" * 60)
print("RF Receiver Tuning Calibration")
print("=" * 60)
print()
print("Instructions:")
print("  1. Turn the blue coil a TINY bit (1/16 turn)")
print("  2. REMOVE the screwdriver from the coil")
print("  3. Press ENTER to measure")
print("  4. Repeat until noise level drops significantly")
print()
print("Direction: Start CLOCKWISE")
print("           Small turns only - about 1/16 of a full rotation")
print()
print("Goal: Find the position with the LOWEST noise count")
print("=" * 60)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RX_PIN, GPIO.IN)

def measure_noise(duration=2.0):
    """Count transitions over a period"""
    count = 0
    last_state = GPIO.input(RX_PIN)
    start_time = time.time()
    
    while time.time() - start_time < duration:
        current_state = GPIO.input(RX_PIN)
        if current_state != last_state:
            count += 1
            last_state = current_state
        time.sleep(0.00005)  # 50µs
    
    return count

# Track measurements
measurements = []
best_noise = float('inf')
best_position = 0

print()
print("Let's measure the STARTING position first.")
input("Press ENTER to measure current position (don't turn anything yet)...")
print("Measuring for 2 seconds...")
noise = measure_noise(2.0)
measurements.append(noise)
best_noise = noise
best_position = 0

print(f"\n📊 Position 0 (starting): {noise} transitions")
print(f"   Noise rate: ~{noise/2:.0f} transitions/sec")
print()

position = 1
try:
    while True:
        print("-" * 40)
        print(f"Turn #{position}:")
        print("  1. Turn coil CLOCKWISE ~1/16 turn")
        print("  2. REMOVE screwdriver")
        input("  3. Press ENTER when ready to measure...")
        
        print("Measuring for 2 seconds (keep hands away)...")
        noise = measure_noise(2.0)
        measurements.append(noise)
        
        # Compare to best
        change = noise - best_noise
        change_pct = (change / best_noise) * 100 if best_noise > 0 else 0
        
        if noise < best_noise:
            best_noise = noise
            best_position = position
            status = "⬇️  BETTER! (New best)"
        elif noise > best_noise * 1.2:
            status = "⬆️  WORSE (going wrong direction?)"
        else:
            status = "➡️  Similar"
        
        print(f"\n📊 Position {position}: {noise} transitions")
        print(f"   Noise rate: ~{noise/2:.0f} transitions/sec")
        print(f"   Change from start: {change:+d} ({change_pct:+.1f}%)")
        print(f"   Status: {status}")
        print(f"\n   🏆 Best so far: Position {best_position} with {best_noise} transitions")
        
        # Check if we should stop or change direction
        if noise < 500:
            print("\n🎉 EXCELLENT! Noise is very low now!")
            print("   This might be a good setting. Try the self-test!")
            resp = input("   Continue tuning? (y/n): ").strip().lower()
            if resp != 'y':
                break
        
        if position >= 16:  # Full rotation (16 x 1/16)
            print("\n⚠️  You've done a full rotation.")
            resp = input("   Try counter-clockwise from start? (y/n): ").strip().lower()
            if resp == 'y':
                print("\n   Return coil to starting position, then we'll go counter-clockwise.")
                input("   Press ENTER when back at start...")
                position = 0
                print("   Now turn COUNTER-CLOCKWISE each time.")
        
        position += 1
        print()

except KeyboardInterrupt:
    print("\n\nStopped by user")

finally:
    GPIO.cleanup()

print()
print("=" * 60)
print("CALIBRATION SUMMARY")
print("=" * 60)
print()
print("All measurements:")
for i, m in enumerate(measurements):
    marker = " 👈 BEST" if i == best_position else ""
    print(f"  Position {i}: {m} transitions ({m/2:.0f}/sec){marker}")

print()
print(f"🏆 Best position: {best_position}")
print(f"   Noise level: {best_noise} transitions ({best_noise/2:.0f}/sec)")
print()

if best_noise < 1000:
    print("✅ Good noise level! Try running the self-test:")
    print("   python3 src/RFController/debug_self_test.py")
elif best_noise < 2000:
    print("⚠️  Moderate noise level. Might work, try the self-test.")
else:
    print("❌ Still high noise. May need a better receiver module (RXB6).")
