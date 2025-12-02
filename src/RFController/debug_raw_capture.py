#!/usr/bin/env python3
"""
Raw RF Signal Capture and Analysis
Captures precise timing data to reverse-engineer the remote's protocol.
"""

import time
import RPi.GPIO as GPIO

GPIO_PIN = 27

print("=" * 60)
print("Raw RF Signal Capture")
print("=" * 60)
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN)

def capture_signal(timeout=5):
    """Capture raw signal timings"""
    pulses = []
    last_state = GPIO.input(GPIO_PIN)
    last_time = time.time()
    start_time = last_time
    
    while time.time() - start_time < timeout:
        current_state = GPIO.input(GPIO_PIN)
        now = time.time()
        
        if current_state != last_state:
            pulse_us = int((now - last_time) * 1000000)
            pulses.append((pulse_us, last_state))
            last_time = now
            last_state = current_state
    
    return pulses

def find_signal_bursts(pulses, min_gap=5000):
    """Find distinct signal bursts separated by gaps"""
    bursts = []
    current_burst = []
    
    for pulse_us, state in pulses:
        if pulse_us > min_gap and current_burst:
            # Gap detected - save current burst
            if len(current_burst) > 20:  # Real signals have many pulses
                bursts.append(current_burst)
            current_burst = []
        else:
            current_burst.append((pulse_us, state))
    
    if len(current_burst) > 20:
        bursts.append(current_burst)
    
    return bursts

def analyze_burst(burst):
    """Analyze a signal burst to find the encoding pattern"""
    # Get all pulse durations
    durations = [p[0] for p in burst]
    
    # Find distinct pulse lengths (cluster similar values)
    pulse_types = {}
    for d in durations:
        # Round to nearest 50µs
        rounded = round(d / 50) * 50
        if rounded > 0:
            pulse_types[rounded] = pulse_types.get(rounded, 0) + 1
    
    # Sort by frequency
    sorted_types = sorted(pulse_types.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'pulse_count': len(burst),
        'duration_ms': sum(durations) / 1000,
        'common_pulses': sorted_types[:6],
        'raw_durations': durations[:50]  # First 50 for pattern analysis
    }

print("Instructions:")
print("1. First capture: DON'T press any buttons (baseline)")
print("2. Second capture: Press ONE button multiple times")
print("3. Third capture: Press a DIFFERENT button multiple times")
print()

# Capture 1: Baseline (no buttons)
input("Press ENTER for baseline capture (don't press remote)...")
print("Capturing baseline for 3 seconds...")
baseline_pulses = capture_signal(3)
baseline_bursts = find_signal_bursts(baseline_pulses)
print(f"Baseline: {len(baseline_bursts)} noise bursts detected")

# Capture 2: Button 1
print()
input("Press ENTER, then press ONE button repeatedly for 5 seconds...")
print("Capturing...")
button1_pulses = capture_signal(5)
button1_bursts = find_signal_bursts(button1_pulses)
print(f"Button 1: {len(button1_bursts)} signal bursts detected")

# Capture 3: Button 2
print()
input("Press ENTER, then press a DIFFERENT button repeatedly for 5 seconds...")
print("Capturing...")
button2_pulses = capture_signal(5)
button2_bursts = find_signal_bursts(button2_pulses)
print(f"Button 2: {len(button2_bursts)} signal bursts detected")

# Analyze results
print()
print("=" * 60)
print("ANALYSIS")
print("=" * 60)

if button1_bursts:
    print("\n📊 Button 1 Signal Analysis:")
    # Analyze the longest burst (likely most complete)
    longest = max(button1_bursts, key=len)
    analysis = analyze_burst(longest)
    print(f"   Pulses per transmission: {analysis['pulse_count']}")
    print(f"   Signal duration: {analysis['duration_ms']:.1f}ms")
    print(f"   Common pulse widths (µs, count):")
    for width, count in analysis['common_pulses']:
        print(f"      {width}µs: {count} times")
    print(f"\n   First 30 pulse timings (µs):")
    print(f"   {analysis['raw_durations'][:30]}")

if button2_bursts:
    print("\n📊 Button 2 Signal Analysis:")
    longest = max(button2_bursts, key=len)
    analysis = analyze_burst(longest)
    print(f"   Pulses per transmission: {analysis['pulse_count']}")
    print(f"   Signal duration: {analysis['duration_ms']:.1f}ms")
    print(f"   Common pulse widths (µs, count):")
    for width, count in analysis['common_pulses']:
        print(f"      {width}µs: {count} times")
    print(f"\n   First 30 pulse timings (µs):")
    print(f"   {analysis['raw_durations'][:30]}")

# Try to identify protocol
print()
print("=" * 60)
print("PROTOCOL IDENTIFICATION")
print("=" * 60)

if button1_bursts:
    longest = max(button1_bursts, key=len)
    analysis = analyze_burst(longest)
    common = [w for w, c in analysis['common_pulses'][:4]]
    
    # Check for common protocols
    print("\nBased on pulse widths, your remote might use:")
    
    # PT2262/PT2272 (common): ~350µs short, ~1050µs long
    if any(250 <= w <= 450 for w in common) and any(900 <= w <= 1200 for w in common):
        print("  ✓ PT2262/PT2272 (EV1527) - Most common 433MHz protocol")
        short_pulse = [w for w in common if 250 <= w <= 450][0]
        print(f"    Estimated pulse length: {short_pulse}µs")
        print(f"    Try: rpi-rf_receive -g 27")
    
    # Check for longer pulses (some protocols)
    if any(100 <= w <= 200 for w in common) and any(400 <= w <= 600 for w in common):
        print("  ✓ Might be protocol 2 or 3 (shorter pulses)")
    
    if any(500 <= w <= 700 for w in common):
        print("  ✓ Might be protocol 4 or 5 (medium pulses)")
    
    print()
    print("If rpi-rf still doesn't decode, we can write a custom decoder")
    print("using these exact timings.")

GPIO.cleanup()
