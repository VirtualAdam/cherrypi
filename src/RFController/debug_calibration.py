#!/usr/bin/env python3
"""
RF Calibration Test
Since we know the receiver CAN decode signals, this test fine-tunes
the timing to get exact code matches.
"""

import time
import RPi.GPIO as GPIO

TX_PIN = 17
RX_PIN = 27
TEST_CODE = 1332531

print("=" * 70)
print("RF CALIBRATION TEST")
print("=" * 70)
print()
print("We know the receiver works (got 46 decodes)!")
print("Now let's fine-tune to get exact matches.")
print()

GPIO.setmode(GPIO.BCM)
GPIO.setup(RX_PIN, GPIO.IN)
GPIO.setup(TX_PIN, GPIO.OUT, initial=GPIO.LOW)

def tx_code_raw(code, pulse_length, protocol=1, repeats=10):
    """Transmit using raw GPIO with precise timing"""
    protocols = {
        1: (1, 3, 31),
        2: (1, 2, 10),
        3: (1, 4, 31),
        4: (1, 3, 15),
        5: (2, 3, 31),
    }
    
    short_mult, long_mult, sync_mult = protocols.get(protocol, protocols[1])
    short = pulse_length
    long = pulse_length * long_mult // short_mult
    sync = pulse_length * sync_mult
    
    bits = format(code, '024b')
    
    for _ in range(repeats):
        # Sync
        GPIO.output(TX_PIN, GPIO.HIGH)
        time.sleep(short / 1000000)
        GPIO.output(TX_PIN, GPIO.LOW)
        time.sleep(sync / 1000000)
        
        # Data
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
        
        time.sleep(0.005)

def capture_and_decode(duration=2.0, expected_pulse=189):
    """Capture and decode with multiple tolerance levels"""
    # Capture
    timings = []
    last_state = GPIO.input(RX_PIN)
    last_time = time.time()
    start = last_time
    
    while time.time() - start < duration:
        state = GPIO.input(RX_PIN)
        if state != last_state:
            timings.append(int((time.time() - last_time) * 1000000))
            last_time = time.time()
            last_state = state
    
    if len(timings) < 40:
        return []
    
    results = []
    
    # Try different pulse lengths and tolerances
    for test_pulse in range(expected_pulse - 80, expected_pulse + 100, 10):
        for tolerance in [0.25, 0.35, 0.45, 0.55]:
            short = test_pulse
            long = test_pulse * 3
            
            bits = []
            i = 0
            while i < len(timings) - 1:
                t1, t2 = timings[i], timings[i + 1]
                
                if t1 > long * 5 or t2 > long * 5:
                    i += 1
                    continue
                
                tol = tolerance
                if (abs(t1 - short) < short * tol and abs(t2 - long) < long * tol):
                    bits.append(0)
                    i += 2
                elif (abs(t1 - long) < long * tol and abs(t2 - short) < short * tol):
                    bits.append(1)
                    i += 2
                else:
                    i += 1
            
            if 20 <= len(bits) <= 28:
                code = 0
                for b in bits[:24]:
                    code = (code << 1) | b
                if code > 1000:
                    results.append({
                        'code': code,
                        'pulse': test_pulse,
                        'tolerance': tolerance,
                        'bits': len(bits)
                    })
    
    return results

# Test with focused parameters
print("Phase 1: Finding exact timing...")
print("-" * 70)

best_results = []
test_configs = [
    (189, 1),  # Your current config
    (180, 1), (185, 1), (190, 1), (195, 1), (200, 1),
    (189, 2), (189, 3), (189, 4), (189, 5),
]

for pulse, proto in test_configs:
    print(f"Testing pulse={pulse}µs, protocol={proto}...", end=" ", flush=True)
    
    # Transmit
    tx_code_raw(TEST_CODE, pulse, proto, repeats=20)
    time.sleep(0.1)
    
    # Capture during transmission
    import threading
    results = []
    
    def capture():
        nonlocal results
        results = capture_and_decode(duration=2.5, expected_pulse=pulse)
    
    cap_thread = threading.Thread(target=capture)
    cap_thread.start()
    time.sleep(0.3)
    tx_code_raw(TEST_CODE, pulse, proto, repeats=30)
    cap_thread.join()
    
    # Check results
    matches = [r for r in results if r['code'] == TEST_CODE]
    close = [r for r in results if abs(r['code'] - TEST_CODE) < TEST_CODE * 0.1]
    
    if matches:
        print(f"✓ EXACT MATCH!")
        best_results.extend(matches)
    elif close:
        print(f"~ Close: {[r['code'] for r in close[:3]]}")
    elif results:
        print(f"✗ Got: {results[0]['code']}")
    else:
        print("✗ No decode")
    
    time.sleep(0.2)

print()
print("=" * 70)

# Phase 2: Bit-level analysis
print("\nPhase 2: Bit-level analysis...")
print("-" * 70)

expected_bits = format(TEST_CODE, '024b')
print(f"Expected code {TEST_CODE} = {expected_bits}")
print()

# Transmit and capture raw for analysis
print("Capturing raw signal for bit analysis...")
tx_code_raw(TEST_CODE, 189, 1, repeats=5)

import threading
raw_timings = []

def raw_capture():
    global raw_timings
    raw_timings = []
    last_state = GPIO.input(RX_PIN)
    last_time = time.time()
    start = last_time
    while time.time() - start < 1.5:
        state = GPIO.input(RX_PIN)
        if state != last_state:
            raw_timings.append((int((time.time() - last_time) * 1000000), last_state))
            last_time = time.time()
            last_state = state

cap_thread = threading.Thread(target=raw_capture)
cap_thread.start()
time.sleep(0.2)
tx_code_raw(TEST_CODE, 189, 1, repeats=15)
cap_thread.join()

# Analyze timing distribution
if raw_timings:
    durations = [t[0] for t in raw_timings if t[0] < 3000]
    if durations:
        print(f"Captured {len(durations)} pulses")
        
        # Find clusters
        short_pulses = [d for d in durations if 100 < d < 400]
        long_pulses = [d for d in durations if 400 < d < 1000]
        
        if short_pulses:
            avg_short = sum(short_pulses) / len(short_pulses)
            print(f"Short pulses: avg={avg_short:.0f}µs (n={len(short_pulses)})")
        
        if long_pulses:
            avg_long = sum(long_pulses) / len(long_pulses)
            print(f"Long pulses: avg={avg_long:.0f}µs (n={len(long_pulses)})")
        
        if short_pulses and long_pulses:
            ratio = avg_long / avg_short
            print(f"Ratio: {ratio:.2f} (expected ~3.0 for protocol 1)")
            
            # Suggest optimal settings
            optimal_pulse = int(avg_short)
            print(f"\n📝 SUGGESTED SETTINGS:")
            print(f"   pulse_length: {optimal_pulse}")
            
            if 2.5 < ratio < 3.5:
                print(f"   protocol: 1 (ratio matches)")
            elif 1.8 < ratio < 2.5:
                print(f"   protocol: 2 (ratio matches)")
            elif 3.5 < ratio < 4.5:
                print(f"   protocol: 3 (ratio matches)")

GPIO.cleanup()

print()
print("=" * 70)
print("CALIBRATION COMPLETE")
print("=" * 70)

if best_results:
    print(f"\n🎉 FOUND {len(best_results)} EXACT MATCHES!")
    print(f"\nUse these settings in config.json:")
    r = best_results[0]
    print(f'   "pulse_length": {r["pulse"]},')
    print(f'   "protocol": 1')
else:
    print("\n⚠️  No exact matches found, but receiver IS working.")
    print("   The timing might need hardware adjustment (tuning coil)")
    print("   or the decoder tolerance needs tweaking.")
