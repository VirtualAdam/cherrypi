#!/usr/bin/env python3
"""
RF Bit Analysis - Compare transmitted vs received bits
"""

import time
import RPi.GPIO as GPIO

TX_PIN = 17
RX_PIN = 27
TEST_CODE = 1332531
PULSE = 189

print("=" * 70)
print("RF BIT-BY-BIT ANALYSIS")
print("=" * 70)
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(RX_PIN, GPIO.IN)
GPIO.setup(TX_PIN, GPIO.OUT, initial=GPIO.LOW)

expected_bits = format(TEST_CODE, '024b')
print(f"Expected: {TEST_CODE} = {expected_bits}")
print()

def tx_and_capture(code, pulse, repeats=20):
    """Transmit while capturing"""
    timings = []
    
    # Start capture in background
    import threading
    capturing = [True]
    
    def capture_thread():
        last_state = GPIO.input(RX_PIN)
        last_time = time.time()
        while capturing[0]:
            state = GPIO.input(RX_PIN)
            if state != last_state:
                timings.append((int((time.time() - last_time) * 1000000), last_state))
                last_time = time.time()
                last_state = state
            time.sleep(0.00001)
    
    cap = threading.Thread(target=capture_thread)
    cap.start()
    
    time.sleep(0.1)  # Let capture start
    
    # Transmit
    bits = format(code, '024b')
    short = pulse
    long = pulse * 3
    sync = pulse * 31
    
    for _ in range(repeats):
        GPIO.output(TX_PIN, GPIO.HIGH)
        time.sleep(short / 1000000)
        GPIO.output(TX_PIN, GPIO.LOW)
        time.sleep(sync / 1000000)
        
        for bit in bits:
            if bit == '0':
                GPIO.output(TX_PIN, GPIO.HIGH)
                time.sleep(short / 1000000)
                GPIO.output(TX_PIN, GPIO.LOW)
                time.sleep(long / 1000000)
            else:
                GPIO.output(TX_PIN, GPIO.HIGH)
                time.sleep(long / 1000000)
                GPIO.output(TX_PIN, GPIO.LOW)
                time.sleep(short / 1000000)
        time.sleep(0.01)
    
    time.sleep(0.2)
    capturing[0] = False
    cap.join()
    
    return timings

print("Transmitting and capturing...")
timings = tx_and_capture(TEST_CODE, PULSE, repeats=15)
print(f"Captured {len(timings)} transitions")
print()

# Analyze timing distribution
durations = [t[0] for t in timings if 50 < t[0] < 5000]
if not durations:
    print("No valid pulses captured!")
    GPIO.cleanup()
    exit()

# Find pulse clusters
short_pulses = [d for d in durations if 100 < d < 350]
long_pulses = [d for d in durations if 350 < d < 900]

if short_pulses and long_pulses:
    avg_short = sum(short_pulses) / len(short_pulses)
    avg_long = sum(long_pulses) / len(long_pulses)
    print(f"Detected pulse widths:")
    print(f"  Short: {avg_short:.0f}µs (n={len(short_pulses)})")
    print(f"  Long: {avg_long:.0f}µs (n={len(long_pulses)})")
    print(f"  Ratio: {avg_long/avg_short:.2f}")
    print()
    
    # Decode using detected values
    decoded_bits = []
    i = 0
    while i < len(durations) - 1:
        t1 = durations[i]
        t2 = durations[i + 1]
        
        # Skip sync
        if t1 > avg_long * 3 or t2 > avg_long * 3:
            if decoded_bits:  # End of a code
                break
            i += 1
            continue
        
        # Decode bit
        t1_short = abs(t1 - avg_short) < avg_short * 0.4
        t1_long = abs(t1 - avg_long) < avg_long * 0.4
        t2_short = abs(t2 - avg_short) < avg_short * 0.4
        t2_long = abs(t2 - avg_long) < avg_long * 0.4
        
        if t1_short and t2_long:
            decoded_bits.append('0')
            i += 2
        elif t1_long and t2_short:
            decoded_bits.append('1')
            i += 2
        else:
            i += 1
    
    if len(decoded_bits) >= 20:
        decoded_str = ''.join(decoded_bits[:24])
        decoded_code = int(decoded_str, 2) if len(decoded_str) == 24 else 0
        
        print(f"Decoded:  {decoded_code} = {decoded_str}")
        print(f"Expected: {TEST_CODE} = {expected_bits}")
        print()
        
        # Compare bit by bit
        if len(decoded_str) == 24:
            diff_count = sum(1 for a, b in zip(decoded_str, expected_bits) if a != b)
            print(f"Bit differences: {diff_count}/24")
            
            if diff_count == 0:
                print("🎉 PERFECT MATCH!")
            elif diff_count == 24:
                # Try inverted
                inverted = ''.join('1' if b == '0' else '0' for b in decoded_str)
                inv_code = int(inverted, 2)
                if inv_code == TEST_CODE:
                    print("⚠️  Bits are INVERTED! Need to flip 0/1 in decoder.")
            elif diff_count < 5:
                print("Very close! Timing tolerance might need adjustment.")
            else:
                # Check if shifted
                for shift in range(-4, 5):
                    if shift == 0:
                        continue
                    if shift > 0:
                        shifted = decoded_str[shift:] + '0' * shift
                    else:
                        shifted = '0' * (-shift) + decoded_str[:shift]
                    
                    shifted_code = int(shifted, 2) if len(shifted) == 24 else 0
                    if shifted_code == TEST_CODE:
                        print(f"⚠️  Bits are SHIFTED by {shift}! Sync detection issue.")
                        break
                    
                    diff = sum(1 for a, b in zip(shifted, expected_bits) if a != b)
                    if diff < 3:
                        print(f"   With shift {shift}: only {diff} differences")
    else:
        print(f"Only got {len(decoded_bits)} bits (need 24)")
else:
    print("Could not identify distinct short/long pulses")
    print(f"All durations: {sorted(set(durations))[:20]}")

GPIO.cleanup()
print()
print("=" * 70)
