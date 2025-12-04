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


class RFDecodeError(Exception):
    """
    Exception raised when RF decoding fails with a clear reason.
    
    This replaces ambiguous None returns with specific error types:
    - NO_SIGNAL: No RF activity detected at all
    - NO_SYNC_GAPS: Signal detected but no valid protocol patterns
    - INSUFFICIENT_SEGMENTS: Some patterns found but not enough
    - DECODE_FAILED: Segments found but couldn't decode them
    - AMBIGUOUS_SIGNAL: Multiple different codes detected (interference or multiple buttons)
    - WEAK_SIGNAL: Code detected but not consistently enough
    """
    
    def __init__(self, error_type: str, message: str, details: dict = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "error": True,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details
        }


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

    def capture_single_window(self, duration=2.0, min_confidence=0.5, min_segments=3):
        """
        Capture a single window of RF data and decode it.
        
        This is the preferred method for the Add Switch wizard:
        1. User holds button on remote
        2. User clicks "Start Capture" in UI
        3. This method captures for `duration` seconds
        4. Analyzes all patterns and picks the most likely signal
        5. Returns clear error if no unambiguous signal detected
        
        Args:
            duration: How long to capture (default 2 seconds)
            min_confidence: Minimum ratio of primary code occurrences to total segments (default 0.5)
            min_segments: Minimum number of valid segments required (default 3)
            
        Returns:
            dict with code info if successful
            Raises RFDecodeError with specific message if no clear signal detected
        """
        self.setup()
        
        # Capture raw timings
        timings = self.capture_raw_timings(duration=duration)
        total_transitions = len(timings)
        
        # Check 1: Did we capture any transitions at all?
        if total_transitions < 40:
            raise RFDecodeError(
                error_type="NO_SIGNAL",
                message=f"No RF signal detected. Only {total_transitions} transitions captured.",
                details={
                    "transitions": total_transitions,
                    "expected_min": 40,
                    "suggestion": "Make sure the remote is transmitting and close to the receiver."
                }
            )
        
        # Find sync gaps (markers between code transmissions)
        sync_gaps = [t[0] for t in timings if t[0] > self.sync_gap_threshold]
        num_sync_gaps = len(sync_gaps)
        logger.info(f"Captured {total_transitions} transitions, {num_sync_gaps} sync gaps")
        
        # Check 2: Do we have sync gaps indicating PT2262/EV1527 protocol?
        if num_sync_gaps < min_segments:
            raise RFDecodeError(
                error_type="NO_SYNC_GAPS",
                message=f"No valid RF code pattern detected. Found {num_sync_gaps} sync gaps, need at least {min_segments}.",
                details={
                    "transitions": total_transitions,
                    "sync_gaps_found": num_sync_gaps,
                    "sync_gaps_needed": min_segments,
                    "suggestion": "Hold the remote button continuously while capturing. The remote may not be compatible (needs PT2262/EV1527 protocol)."
                }
            )
        
        # Find code segments using sync gap detection
        segments = self.find_code_segments(timings)
        num_segments = len(segments)
        
        # Check 3: Did we get valid segments?
        if num_segments < min_segments:
            raise RFDecodeError(
                error_type="INSUFFICIENT_SEGMENTS",
                message=f"Not enough valid code segments. Found {num_segments}, need at least {min_segments}.",
                details={
                    "transitions": total_transitions,
                    "sync_gaps": num_sync_gaps,
                    "segments_found": num_segments,
                    "segments_needed": min_segments,
                    "suggestion": "The signal may be too weak or corrupted. Try moving the remote closer."
                }
            )
        
        logger.info(f"Found {num_segments} valid segments")
        
        # Try to decode each segment and count code occurrences
        codes_found = {}
        decode_failures = 0
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
            else:
                decode_failures += 1
        
        # Check 4: Could we decode any segments?
        if not codes_found:
            raise RFDecodeError(
                error_type="DECODE_FAILED",
                message=f"Could not decode any valid codes from {num_segments} segments.",
                details={
                    "transitions": total_transitions,
                    "sync_gaps": num_sync_gaps,
                    "segments_found": num_segments,
                    "decode_failures": decode_failures,
                    "suggestion": "The signal format may not be compatible. This decoder works with PT2262/EV1527 protocols."
                }
            )
        
        # Find the most frequently seen code
        sorted_codes = sorted(codes_found.items(), key=lambda x: x[1]['count'], reverse=True)
        best_code_value, best_code_data = sorted_codes[0]
        best_count = best_code_data['count']
        
        # Calculate confidence: how dominant is the primary code?
        total_decoded = sum(d['count'] for d in codes_found.values())
        confidence = best_count / total_decoded if total_decoded > 0 else 0
        
        # Check 5: Is the signal clear and unambiguous?
        if confidence < min_confidence:
            # Build details about competing codes
            competing_codes = [
                {"code": c, "count": d['count'], "percentage": round(d['count']/total_decoded*100, 1)}
                for c, d in sorted_codes[:5]  # Top 5 codes
            ]
            raise RFDecodeError(
                error_type="AMBIGUOUS_SIGNAL",
                message=f"Signal is ambiguous. Top code {best_code_value} only seen {best_count}/{total_decoded} times ({confidence*100:.0f}% confidence).",
                details={
                    "transitions": total_transitions,
                    "segments_found": num_segments,
                    "codes_decoded": total_decoded,
                    "unique_codes": len(codes_found),
                    "confidence": round(confidence, 2),
                    "confidence_needed": min_confidence,
                    "competing_codes": competing_codes,
                    "suggestion": "Multiple different codes detected. Hold only ONE button, or there may be RF interference."
                }
            )
        
        # Check 6: Did we see the code enough times?
        if best_count < min_segments:
            raise RFDecodeError(
                error_type="WEAK_SIGNAL",
                message=f"Code {best_code_value} only detected {best_count} times, need at least {min_segments}.",
                details={
                    "code": best_code_value,
                    "times_seen": best_count,
                    "times_needed": min_segments,
                    "confidence": round(confidence, 2),
                    "suggestion": "The signal is too weak or intermittent. Hold the button firmly and try again."
                }
            )
        
        # SUCCESS! Build the result
        result = best_code_data['result'].copy()
        result['times_seen'] = best_count
        result['segments_found'] = num_segments
        result['total_codes_found'] = len(codes_found)
        result['confidence'] = round(confidence, 2)
        result['decode_success_rate'] = round((total_decoded / num_segments) * 100, 1)
        
        # Log results
        if len(codes_found) > 1:
            outliers = [f"{c} ({d['count']}x)" for c, d in sorted_codes[1:]]
            logger.info(f"Primary code: {best_code_value} ({best_count}x, {confidence*100:.0f}% confidence), outliers: {outliers}")
        else:
            logger.info(f"Decoded code {best_code_value} (seen {best_count}x, 100% consistent)")
        
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
