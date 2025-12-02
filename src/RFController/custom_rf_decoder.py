#!/usr/bin/env python3
"""
Custom RF Decoder for CherryPi
Uses direct GPIO timing analysis instead of rpi_rf library
Based on the calibration that achieved a perfect 24/24 bit match
"""

import time
import RPi.GPIO as GPIO

class CustomRFDecoder:
    """
    Custom RF decoder using direct GPIO timing analysis.
    Calibrated for 275µs short pulse, ~640µs long pulse (ratio ~2.33)
    """
    
    def __init__(self, gpio_pin, tolerance=0.35):
        self.gpio_pin = gpio_pin
        self.tolerance = tolerance
        self.short_pulse = 275  # Calibrated value
        self.long_pulse = 640   # Calibrated value
        self._setup_done = False
        
    def setup(self):
        """Initialize GPIO"""
        if not self._setup_done:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.IN)
            self._setup_done = True
    
    def cleanup(self):
        """Cleanup GPIO"""
        if self._setup_done:
            try:
                GPIO.cleanup(self.gpio_pin)
            except:
                pass
            self._setup_done = False
    
    def capture_timings(self, duration=2.0):
        """Capture raw pulse timings from GPIO"""
        self.setup()
        
        timings = []
        last_state = GPIO.input(self.gpio_pin)
        last_time = time.time()
        start_time = last_time
        
        while time.time() - start_time < duration:
            current_state = GPIO.input(self.gpio_pin)
            if current_state != last_state:
                pulse_us = int((time.time() - last_time) * 1000000)
                timings.append((pulse_us, last_state))
                last_time = time.time()
                last_state = current_state
        
        return timings
    
    def decode_timings(self, timings):
        """
        Decode captured timings into RF code.
        Returns dict with code, pulse info, or None if no valid decode.
        """
        if len(timings) < 40:
            return None
        
        # Extract just durations
        durations = [t[0] for t in timings]
        
        # Find short and long pulses dynamically
        short_pulses = [d for d in durations if 150 < d < 450]
        long_pulses = [d for d in durations if 450 < d < 1200]
        
        if len(short_pulses) < 10 or len(long_pulses) < 10:
            return None
        
        short_avg = sum(short_pulses) / len(short_pulses)
        long_avg = sum(long_pulses) / len(long_pulses)
        
        # Decode bits using PT2262/EV1527 encoding
        # 0 = short HIGH, long LOW
        # 1 = long HIGH, short LOW
        bits = []
        i = 0
        
        while i < len(durations) - 1:
            t1 = durations[i]
            t2 = durations[i + 1]
            
            # Skip sync pulses (very long)
            if t1 > long_avg * 4 or t2 > long_avg * 4:
                i += 1
                continue
            
            tol = self.tolerance
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
        
        # Valid codes are typically 24 bits
        if 20 <= len(bits) <= 28:
            code = 0
            for b in bits[:24]:
                code = (code << 1) | b
            
            if code > 1000:  # Filter noise
                return {
                    'code': code,
                    'pulselength': int(short_avg),
                    'protocol': 1,
                    'bits': len(bits),
                    'short_pulse': int(short_avg),
                    'long_pulse': int(long_avg)
                }
        
        return None
    
    def receive(self, timeout=30):
        """
        Listen for RF codes with timeout.
        Returns decoded result or None on timeout.
        """
        self.setup()
        start_time = time.time()
        last_code = None
        last_code_time = 0
        
        while time.time() - start_time < timeout:
            # Capture a short window
            timings = self.capture_timings(duration=0.5)
            
            if len(timings) > 40:
                result = self.decode_timings(timings)
                
                if result and result['code'] > 1000:
                    # Debounce - same code within 1 second is ignored
                    now = time.time()
                    if result['code'] != last_code or (now - last_code_time) > 1.0:
                        last_code = result['code']
                        last_code_time = now
                        return result
            
            time.sleep(0.05)
        
        return None


# Test if run directly
if __name__ == "__main__":
    print("Custom RF Decoder Test")
    print("=" * 50)
    
    decoder = CustomRFDecoder(gpio_pin=27)
    
    try:
        print("Listening for RF codes... (press Ctrl+C to stop)")
        print()
        
        while True:
            result = decoder.receive(timeout=10)
            
            if result:
                print(f"📡 Received code: {result['code']}")
                print(f"   Pulse length: {result['pulselength']}µs")
                print(f"   Short/Long: {result['short_pulse']}µs / {result['long_pulse']}µs")
                print()
            else:
                print("... no code received (timeout)")
                
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        decoder.cleanup()
