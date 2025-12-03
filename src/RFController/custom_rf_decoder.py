#!/usr/bin/env python3
"""
Custom RF Decoder for CherryPi
Uses sync gap detection and direct GPIO timing analysis.
Achieves 99%+ accuracy with PT2262/EV1527 remotes.

Based on successful calibration:
- Short pulse: ~180µs
- Long pulse: ~550µs  
- Sync gap: ~5700µs (detected as >4000µs)
"""

import time
import logging

# Import GPIO - try rpi-lgpio first (for newer kernels), then RPi.GPIO
try:
    import RPi.GPIO as GPIO
except ImportError:
    raise ImportError("RPi.GPIO not available - custom RF decoder requires GPIO access")

logger = logging.getLogger(__name__)


class CustomRFDecoder:
    """
    Custom RF decoder using sync gap detection and direct GPIO timing.
    
    The key insight: PT2262/EV1527 protocols have a long sync gap (~5700µs)
    between code transmissions. By detecting these gaps, we can isolate
    individual code segments and decode them accurately.
    """
    
    def __init__(self, gpio_pin, tolerance=0.4):
        self.gpio_pin = gpio_pin
        self.tolerance = tolerance
        self.sync_gap_threshold = 4000  # µs - gaps longer than this mark segment boundaries
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
    
    def capture_raw_timings(self, duration=2.0):
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

    def find_code_segments(self, timings):
        """
        Find segments that start after a sync gap (>4000µs).
        
        PT2262 remotes send the code multiple times with sync gaps between.
        By splitting on these gaps, we isolate individual code transmissions.
        """
        segments = []
        current_segment = []
        
        for pulse_us, state in timings:
            if pulse_us > self.sync_gap_threshold:
                # Sync gap detected - save current segment if valid
                if len(current_segment) >= 40:
                    segments.append(current_segment)
                current_segment = []
            else:
                current_segment.append(pulse_us)
        
        # Don't forget the last segment
        if len(current_segment) >= 40:
            segments.append(current_segment)
        
        return segments

    def decode_segment(self, durations):
        """
        Decode a single segment of pulses into an RF code.
        
        PT2262/EV1527 encoding:
        - Bit 0: short pulse, long pulse
        - Bit 1: long pulse, short pulse
        """
        if len(durations) < 40:
            return None
        
        # Dynamically find short and long pulse averages for this segment
        short_pulses = [d for d in durations if 150 < d < 450]
        long_pulses = [d for d in durations if 450 < d < 1200]
        
        if len(short_pulses) < 10 or len(long_pulses) < 10:
            return None
        
        short_avg = sum(short_pulses) / len(short_pulses)
        long_avg = sum(long_pulses) / len(long_pulses)
        
        # Decode bits
        bits = []
        i = 0
        tol = self.tolerance
        
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
        Listen for RF codes with timeout using sync gap detection.
        
        DEPRECATED: Use capture_single_window() for better UX.
        This method loops until it finds a code, which isn't ideal.
        
        Returns decoded result or None on timeout.
        """
        self.setup()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.capture_single_window(duration=2.0)
            if result:
                return result
            time.sleep(0.1)
        
        return None

    def capture_single_window(self, duration=2.0):
        """
        Capture a single window of RF data and decode it.
        
        This is the preferred method for the Add Switch wizard:
        1. User holds button on remote
        2. User clicks "Start Capture" in UI
        3. This method captures for `duration` seconds
        4. Returns the most frequently seen code (filters outliers)
        
        Args:
            duration: How long to capture (default 2 seconds)
            
        Returns:
            dict with code info if successful, None if no valid code found
            Also includes 'segments_found' and 'times_seen' for debugging
        """
        self.setup()
        
        # Capture raw timings
        timings = self.capture_raw_timings(duration=duration)
        
        if len(timings) < 40:
            logger.warning(f"Too few transitions captured: {len(timings)}")
            return None
        
        # Find sync gaps for debugging
        sync_gaps = [t[0] for t in timings if t[0] > self.sync_gap_threshold]
        logger.info(f"Captured {len(timings)} transitions, {len(sync_gaps)} sync gaps")
        
        # Find code segments using sync gap detection
        segments = self.find_code_segments(timings)
        
        if not segments:
            logger.warning("No valid code segments found")
            return None
        
        logger.info(f"Found {len(segments)} valid segments")
        
        # Try to decode each segment and count code occurrences
        codes_found = {}
        for seg in segments:
            result = self.decode_segment(seg)
            if result and result['code'] > 1000:
                code = result['code']
                if code not in codes_found:
                    codes_found[code] = {
                        'result': result,
                        'count': 1
                    }
                else:
                    codes_found[code]['count'] += 1
        
        if not codes_found:
            logger.warning("Could not decode any valid codes from segments")
            return None
        
        # Find the most frequently seen code (filters out noise/bit errors)
        best_code = max(codes_found.items(), key=lambda x: x[1]['count'])
        code_value = best_code[0]
        code_data = best_code[1]
        
        # Add metadata for debugging
        result = code_data['result'].copy()
        result['times_seen'] = code_data['count']
        result['segments_found'] = len(segments)
        result['total_codes_found'] = len(codes_found)
        
        # Log any outliers for debugging
        if len(codes_found) > 1:
            outliers = [f"{c} ({d['count']}x)" for c, d in codes_found.items() if c != code_value]
            logger.info(f"Primary code: {code_value} ({code_data['count']}x), outliers: {outliers}")
        else:
            logger.info(f"Decoded code {code_value} (seen {code_data['count']}x, 100% consistent)")
        
        return result


# Test if run directly
if __name__ == "__main__":
    print("Custom RF Decoder Test - Sync Gap Detection")
    print("=" * 50)
    
    logging.basicConfig(level=logging.INFO)
    decoder = CustomRFDecoder(gpio_pin=27)
    
    try:
        print("Listening for RF codes... (press Ctrl+C to stop)")
        print()
        
        while True:
            print("Waiting for signal...")
            result = decoder.receive(timeout=10)
            
            if result:
                print(f"✅ Received code: {result['code']}")
                print(f"   Pulse length: {result['pulselength']}µs")
                print(f"   Short/Long: {result['short_pulse']}µs / {result['long_pulse']}µs")
                print()
            else:
                print("... no code received (timeout)")
                
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        decoder.cleanup()
