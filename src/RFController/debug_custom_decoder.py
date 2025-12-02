#!/usr/bin/env python3
"""
Custom RF Decoder - bypasses rpi_rf library issues
Decodes 433MHz signals directly from GPIO timing data.
Based on PT2262/EV1527 protocol (most common for these remotes).
"""

import time
import RPi.GPIO as GPIO

RX_PIN = 27
TX_PIN = 17

# Protocol parameters (PT2262/EV1527)
# Short pulse + long gap = 0
# Long pulse + short gap = 1
# Sync: very short pulse + very long gap

TOLERANCE = 0.35  # 35% timing tolerance

print("=" * 60)
print("Custom RF Decoder")
print("=" * 60)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RX_PIN, GPIO.IN)

class RFDecoder:
    def __init__(self, gpio_pin):
        self.gpio = gpio_pin
        self.timings = []
        self.last_time = time.time()
        self.last_state = GPIO.input(gpio_pin)
        
    def capture_timings(self, max_timings=200, timeout=0.5):
        """Capture pulse timings"""
        self.timings = []
        self.last_time = time.time()
        self.last_state = GPIO.input(self.gpio)
        start_time = self.last_time
        
        while len(self.timings) < max_timings and (time.time() - start_time) < timeout:
            current_state = GPIO.input(self.gpio)
            now = time.time()
            
            if current_state != self.last_state:
                duration_us = int((now - self.last_time) * 1000000)
                self.timings.append(duration_us)
                self.last_time = now
                self.last_state = current_state
                
        return self.timings
    
    def decode_timings(self, timings):
        """Try to decode captured timings into a code"""
        if len(timings) < 10:
            return None
            
        # Find sync pulse (very long gap, typically 10-40x the short pulse)
        # Then decode the following pulses
        
        # First, find common pulse widths
        short_pulses = []
        long_pulses = []
        
        for t in timings:
            if 100 < t < 600:
                short_pulses.append(t)
            elif 600 < t < 2000:
                long_pulses.append(t)
        
        if not short_pulses or not long_pulses:
            return None
            
        short_avg = sum(short_pulses) / len(short_pulses)
        long_avg = sum(long_pulses) / len(long_pulses)
        
        # Decode bits
        bits = []
        i = 0
        while i < len(timings) - 1:
            t1 = timings[i]
            t2 = timings[i + 1] if i + 1 < len(timings) else 0
            
            # Check for sync (skip it)
            if t1 > long_avg * 3 or t2 > long_avg * 3:
                i += 1
                continue
            
            # Decode bit based on pulse pattern
            is_t1_short = abs(t1 - short_avg) < short_avg * TOLERANCE
            is_t1_long = abs(t1 - long_avg) < long_avg * TOLERANCE
            is_t2_short = abs(t2 - short_avg) < short_avg * TOLERANCE
            is_t2_long = abs(t2 - long_avg) < long_avg * TOLERANCE
            
            if is_t1_short and is_t2_long:
                bits.append(0)
                i += 2
            elif is_t1_long and is_t2_short:
                bits.append(1)
                i += 2
            else:
                i += 1
        
        if len(bits) >= 20:
            # Convert bits to integer
            code = 0
            for bit in bits[:24]:  # Usually 24 bits
                code = (code << 1) | bit
            return {
                'code': code,
                'bits': len(bits),
                'short_pulse': int(short_avg),
                'long_pulse': int(long_avg),
            }
        
        return None

def listen_for_codes(duration=30):
    """Listen and decode RF signals"""
    decoder = RFDecoder(RX_PIN)
    codes_found = []
    start_time = time.time()
    
    print(f"\nListening for {duration} seconds...")
    print("Press buttons on your remote!\n")
    
    while time.time() - start_time < duration:
        timings = decoder.capture_timings(max_timings=150, timeout=0.3)
        
        if len(timings) > 30:
            result = decoder.decode_timings(timings)
            
            if result and result['code'] > 100:  # Filter out noise
                # Check if we've seen this code recently
                if not codes_found or codes_found[-1]['code'] != result['code']:
                    codes_found.append(result)
                    print(f"📡 DECODED: Code={result['code']}")
                    print(f"   Bits: {result['bits']}, Short: {result['short_pulse']}µs, Long: {result['long_pulse']}µs")
                    print()
        
        time.sleep(0.05)
    
    return codes_found

# Test transmitting and receiving
print("\nTest 1: Listen for your REMOTE")
print("-" * 40)
input("Press ENTER, then press buttons on your remote...")
remote_codes = listen_for_codes(15)

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)

if remote_codes:
    print(f"\n✅ Decoded {len(remote_codes)} codes from your remote!")
    print("\nUnique codes found:")
    seen = set()
    for r in remote_codes:
        if r['code'] not in seen:
            seen.add(r['code'])
            print(f"  Code: {r['code']}")
            print(f"    Pulse length: ~{r['short_pulse']}µs")
else:
    print("\n❌ Could not decode any codes.")
    print("   The receiver might need further tuning or replacement.")

GPIO.cleanup()
