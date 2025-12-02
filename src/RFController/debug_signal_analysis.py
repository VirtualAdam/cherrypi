#!/usr/bin/env python3
"""
Advanced RF Signal Analysis
Captures raw timing data to analyze signal patterns even in noisy conditions.
This helps identify if real RF signals are being received amidst the noise.
"""

import time
import RPi.GPIO as GPIO
from collections import Counter

GPIO_PIN = 27  # Physical Pin 13

print("=" * 60)
print("Advanced RF Signal Analysis")
print("=" * 60)
print(f"GPIO Pin: {GPIO_PIN}")
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN)

def capture_timings(duration_seconds=5):
    """Capture pulse timings for analysis"""
    timings = []
    last_state = GPIO.input(GPIO_PIN)
    last_time = time.time()
    start_time = last_time
    
    while time.time() - start_time < duration_seconds:
        current_state = GPIO.input(GPIO_PIN)
        if current_state != last_state:
            now = time.time()
            pulse_duration = int((now - last_time) * 1000000)  # microseconds
            if pulse_duration < 100000:  # Ignore very long pulses (>100ms)
                timings.append((pulse_duration, last_state))
            last_time = now
            last_state = current_state
    
    return timings

def analyze_timings(timings):
    """Look for patterns in the timing data"""
    if not timings:
        return None
    
    # Get just the durations
    durations = [t[0] for t in timings]
    
    # Bucket timings to find common pulse widths
    # RF protocols typically have 2-4 distinct pulse widths
    buckets = {}
    bucket_size = 50  # 50 microsecond buckets
    
    for d in durations:
        bucket = (d // bucket_size) * bucket_size
        buckets[bucket] = buckets.get(bucket, 0) + 1
    
    # Find the most common pulse widths
    sorted_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'total_pulses': len(timings),
        'avg_duration': sum(durations) / len(durations) if durations else 0,
        'min_duration': min(durations) if durations else 0,
        'max_duration': max(durations) if durations else 0,
        'top_buckets': sorted_buckets[:10],
    }

print("This tool captures and analyzes signal timings to detect patterns.")
print()
print("We'll do two captures:")
print("  1. Background noise (DON'T press any buttons)")
print("  2. With signal (PRESS and HOLD a button)")
print()

# Capture 1: Background noise
input("Press ENTER to start background noise capture (5 seconds)...")
print("Capturing background noise - DON'T PRESS ANY BUTTONS...")
noise_timings = capture_timings(5)
noise_analysis = analyze_timings(noise_timings)

print(f"\n📊 Background Noise Analysis:")
print(f"   Total transitions: {noise_analysis['total_pulses']}")
print(f"   Avg pulse width: {noise_analysis['avg_duration']:.0f} µs")
print(f"   Range: {noise_analysis['min_duration']:.0f} - {noise_analysis['max_duration']:.0f} µs")
print(f"   Top pulse widths (µs): ", end="")
print(", ".join([f"{b[0]}" for b in noise_analysis['top_buckets'][:5]]))

# Capture 2: With signal
print()
input("\nPress ENTER, then IMMEDIATELY press and HOLD a button on your remote...")
print("Capturing signal - PRESS AND HOLD A BUTTON NOW...")
signal_timings = capture_timings(5)
signal_analysis = analyze_timings(signal_timings)

print(f"\n📊 Signal + Noise Analysis:")
print(f"   Total transitions: {signal_analysis['total_pulses']}")
print(f"   Avg pulse width: {signal_analysis['avg_duration']:.0f} µs")
print(f"   Range: {signal_analysis['min_duration']:.0f} - {signal_analysis['max_duration']:.0f} µs")
print(f"   Top pulse widths (µs): ", end="")
print(", ".join([f"{b[0]}" for b in signal_analysis['top_buckets'][:5]]))

# Compare
print()
print("=" * 60)
print("COMPARISON")
print("=" * 60)

# Check if signal capture looks different from noise
noise_buckets = set([b[0] for b in noise_analysis['top_buckets'][:5]])
signal_buckets = set([b[0] for b in signal_analysis['top_buckets'][:5]])
new_buckets = signal_buckets - noise_buckets

transition_diff = signal_analysis['total_pulses'] - noise_analysis['total_pulses']
avg_diff = signal_analysis['avg_duration'] - noise_analysis['avg_duration']

print(f"Transition count change: {transition_diff:+d}")
print(f"Average pulse width change: {avg_diff:+.0f} µs")
print(f"New pulse widths in signal: {new_buckets if new_buckets else 'None'}")

if abs(transition_diff) > 1000 or new_buckets or abs(avg_diff) > 100:
    print()
    print("✓ SIGNAL DETECTED! The captures show different patterns.")
    print("  The receiver IS picking up your remote signal!")
    print()
    print("  The rpi_rf library may need different protocol settings.")
    print("  Common 433MHz protocols: protocol 1, 2, 3, 4, 5")
    print("  Try running: rpi-rf_receive -g 27 -p 1")
    print("  Then try protocols 2, 3, 4, 5 if that doesn't work.")
else:
    print()
    print("⚠️  NO SIGNIFICANT DIFFERENCE detected between captures.")
    print()
    print("This suggests the receiver isn't picking up the signal.")
    print("Try:")
    print("  1. Turn the blue tuning coil VERY slowly with a plastic tool")
    print("  2. Switch to 3.3V power (Pin 1 instead of Pin 4)")
    print("  3. Try the other DATA pin on the receiver")
    print("  4. The receiver module may be faulty - try a different one")

GPIO.cleanup()
