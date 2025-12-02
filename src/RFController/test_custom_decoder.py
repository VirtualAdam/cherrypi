#!/usr/bin/env python3
"""
Quick test script for the custom RF decoder.
Run this on the Pi to verify it can capture codes from the remote.

Usage:
    python3 test_custom_decoder.py

Hold a button on your remote, then press Enter.
"""

import time
import sys
import RPi.GPIO as GPIO

# Add current directory to path
sys.path.insert(0, '.')

GPIO_PIN = 27

def capture_raw_timings(duration=2.0):
    """Capture raw pulse timings from GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_PIN, GPIO.IN)
    
    timings = []
    last_state = GPIO.input(GPIO_PIN)
    last_time = time.time()
    start_time = last_time
    
    while time.time() - start_time < duration:
        current_state = GPIO.input(GPIO_PIN)
        if current_state != last_state:
            pulse_us = int((time.time() - last_time) * 1000000)
            timings.append((pulse_us, last_state))
            last_time = time.time()
            last_state = current_state
    
    return timings

def decode_timings(timings):
    """Try to decode captured timings"""
    if len(timings) < 40:
        return None
    
    durations = [t[0] for t in timings]
    
    # Find short and long pulses
    short_pulses = [d for d in durations if 150 < d < 450]
    long_pulses = [d for d in durations if 450 < d < 1200]
    
    if len(short_pulses) < 10 or len(long_pulses) < 10:
        return None
    
    short_avg = sum(short_pulses) / len(short_pulses)
    long_avg = sum(long_pulses) / len(long_pulses)
    
    # Decode bits
    bits = []
    i = 0
    tol = 0.4
    
    while i < len(durations) - 1:
        t1 = durations[i]
        t2 = durations[i + 1]
        
        if t1 > long_avg * 4 or t2 > long_avg * 4:
            i += 1
            continue
        
        is_t1_short = abs(t1 - short_avg) < short_avg * tol
        is_t1_long = abs(t1 - long_avg) < long_avg * tol
        is_t2_short = abs(t2 - short_avg) < short_avg * tol
        is_t2_long = abs(t2 - long_avg) < long_avg * tol
        
        if is_t1_short and is_t2_long:
            bits.append(0)
            i += 2
        elif is_t1_long and is_t2_short:
            bits.append(1)
            i += 2
        else:
            i += 1
    
    if 20 <= len(bits) <= 28:
        code = 0
        for b in bits[:24]:
            code = (code << 1) | b
        
        if code > 1000:
            return {
                'code': code,
                'short_pulse': int(short_avg),
                'long_pulse': int(long_avg),
                'bits': len(bits)
            }
    
    return None

def main():
    print("=" * 60)
    print("Custom RF Decoder Test - Direct GPIO")
    print("=" * 60)
    print(f"GPIO Pin: {GPIO_PIN}")
    print()
    
    try:
        while True:
            print("-" * 40)
            input("Hold button on remote, then press ENTER...")
            print("Capturing for 2 seconds...")
            
            timings = capture_raw_timings(duration=2.0)
            
            print(f"  Captured {len(timings)} transitions")
            
            if len(timings) > 0:
                durations = [t[0] for t in timings]
                short_count = len([d for d in durations if 150 < d < 450])
                long_count = len([d for d in durations if 450 < d < 1200])
                print(f"  Short pulses (150-450µs): {short_count}")
                print(f"  Long pulses (450-1200µs): {long_count}")
            
            result = decode_timings(timings)
            
            if result:
                print()
                print("✅ SUCCESS! Code captured:")
                print(f"   Code:        {result['code']}")
                print(f"   Short pulse: {result['short_pulse']}µs")
                print(f"   Long pulse:  {result['long_pulse']}µs")
                print(f"   Bits:        {result['bits']}")
            else:
                print("❌ Could not decode a valid code")
            
            print()
        
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
