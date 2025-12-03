#!/usr/bin/env python3
"""
Quick test script for the custom RF decoder.
Looks for sync gaps to identify code transmissions.
"""

import time
import sys
import RPi.GPIO as GPIO

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

def find_code_segments(timings):
    """Find segments that start with a sync pulse (long gap > 4000µs)"""
    segments = []
    current_segment = []
    
    for pulse_us, state in timings:
        # Sync gap detection - typically 10000-30000µs for PT2262
        if pulse_us > 4000:
            if len(current_segment) >= 40:
                segments.append(current_segment)
            current_segment = []
        else:
            current_segment.append(pulse_us)
    
    # Don't forget last segment
    if len(current_segment) >= 40:
        segments.append(current_segment)
    
    return segments

def decode_segment(durations):
    """Decode a single segment of pulses"""
    if len(durations) < 40:
        return None
    
    # Find short and long pulses in this segment
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
    print("Custom RF Decoder Test - Sync Gap Detection")
    print("=" * 60)
    print(f"GPIO Pin: {GPIO_PIN}")
    print()
    
    try:
        while True:
            print("-" * 40)
            input("Hold button on remote, then press ENTER...")
            print("Capturing for 2 seconds...")
            
            timings = capture_raw_timings(duration=2.0)
            
            print(f"  Total transitions: {len(timings)}")
            
            # Find sync gaps
            sync_gaps = [t[0] for t in timings if t[0] > 4000]
            print(f"  Sync gaps (>4000µs): {len(sync_gaps)}")
            if sync_gaps[:5]:
                print(f"  First few sync gaps: {sync_gaps[:5]}")
            
            # Find and decode segments
            segments = find_code_segments(timings)
            print(f"  Valid segments found: {len(segments)}")
            
            # Try to decode each segment
            codes_found = {}
            for seg in segments:
                result = decode_segment(seg)
                if result:
                    code = result['code']
                    if code not in codes_found:
                        codes_found[code] = result
                        codes_found[code]['count'] = 1
                    else:
                        codes_found[code]['count'] += 1
            
            if codes_found:
                print()
                print("✅ Codes captured:")
                for code, info in codes_found.items():
                    print(f"   Code: {code} (seen {info['count']}x)")
                    print(f"   Short: {info['short_pulse']}µs, Long: {info['long_pulse']}µs")
            else:
                print("❌ Could not decode any valid codes")
                # Show some debug info about segments
                if segments:
                    print(f"  Segment sizes: {[len(s) for s in segments[:5]]}")
            
            print()
        
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
