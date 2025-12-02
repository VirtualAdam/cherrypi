#!/usr/bin/env python3
"""
ULTIMATE RF Self-Test
Tries every possible combination of protocols, pulse lengths, and decoding methods
to find what works between our transmitter and receiver.
"""

import time
import threading
import RPi.GPIO as GPIO
from collections import defaultdict
from datetime import datetime

TX_PIN = 17
RX_PIN = 27
TEST_CODE = 1332531

# Setup logging to file
LOG_FILE = "/home/baymax/cherrypi/rf_test_results.txt"
log_lines = []

def log(message, also_print=True):
    """Log to both console and file"""
    log_lines.append(message)
    if also_print:
        print(message)

log("=" * 70)
log("ULTIMATE RF SELF-TEST")
log(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("=" * 70)
log("")
log("This test will try EVERYTHING to get the receiver to decode properly.")
log("It will take about 5 minutes. Just let it run!")
log("")
log(f"Transmitter: GPIO {TX_PIN}")
log(f"Receiver: GPIO {RX_PIN}")
log(f"Test code: {TEST_CODE}")
log("")

GPIO.setmode(GPIO.BCM)
GPIO.setup(RX_PIN, GPIO.IN)
GPIO.setup(TX_PIN, GPIO.OUT)

# ============================================================
# PART 1: Raw GPIO Transmitter (bypass rpi_rf for TX)
# ============================================================

def tx_pulse(duration_us):
    """Send a single pulse"""
    GPIO.output(TX_PIN, GPIO.HIGH)
    time.sleep(duration_us / 1000000)
    GPIO.output(TX_PIN, GPIO.LOW)
    time.sleep(duration_us / 1000000)

def tx_code_raw(code, pulse_length, protocol=1, repeats=10):
    """Transmit code using raw GPIO - various protocols"""
    
    # Protocol definitions (short_pulse, long_pulse, sync_multiplier)
    protocols = {
        1: (1, 3, 31),   # Standard PT2262
        2: (1, 2, 10),   # Shorter
        3: (1, 4, 31),   # Longer
        4: (1, 3, 15),   # Different sync
        5: (2, 3, 31),   # Different ratio
    }
    
    if protocol not in protocols:
        protocol = 1
    
    short_mult, long_mult, sync_mult = protocols[protocol]
    short = pulse_length * short_mult
    long = pulse_length * long_mult
    sync = pulse_length * sync_mult
    
    # Convert code to 24 bits
    bits = format(code, '024b')
    
    for _ in range(repeats):
        # Sync pulse
        GPIO.output(TX_PIN, GPIO.HIGH)
        time.sleep(pulse_length / 1000000)
        GPIO.output(TX_PIN, GPIO.LOW)
        time.sleep(sync * pulse_length / 1000000)
        
        # Data bits
        for bit in bits:
            if bit == '0':
                # Short HIGH, Long LOW
                GPIO.output(TX_PIN, GPIO.HIGH)
                time.sleep(short / 1000000)
                GPIO.output(TX_PIN, GPIO.LOW)
                time.sleep(long / 1000000)
            else:
                # Long HIGH, Short LOW
                GPIO.output(TX_PIN, GPIO.HIGH)
                time.sleep(long / 1000000)
                GPIO.output(TX_PIN, GPIO.LOW)
                time.sleep(short / 1000000)
        
        time.sleep(0.01)  # Gap between repeats

# ============================================================
# PART 2: Multiple Receiver Decoders
# ============================================================

class SimpleDecoder:
    """Basic timing-based decoder"""
    def __init__(self, tolerance=0.35):
        self.tolerance = tolerance
        self.timings = []
        self.codes = []
        
    def capture(self, duration=1.0):
        """Capture raw timings"""
        self.timings = []
        last_state = GPIO.input(RX_PIN)
        last_time = time.time()
        start = last_time
        
        while time.time() - start < duration:
            state = GPIO.input(RX_PIN)
            if state != last_state:
                self.timings.append(int((time.time() - last_time) * 1000000))
                last_time = time.time()
                last_state = state
        
        return self.timings
    
    def decode(self, timings, expected_pulse=189):
        """Try to decode timings"""
        if len(timings) < 40:
            return None
        
        # Look for patterns around expected pulse length
        for pulse_test in range(expected_pulse - 100, expected_pulse + 150, 25):
            short = pulse_test
            long = pulse_test * 3
            
            bits = []
            i = 0
            while i < len(timings) - 1:
                t1, t2 = timings[i], timings[i + 1]
                
                # Skip sync pulses
                if t1 > long * 5 or t2 > long * 5:
                    i += 1
                    continue
                
                tol = self.tolerance
                if (abs(t1 - short) < short * tol and abs(t2 - long) < long * tol):
                    bits.append(0)
                    i += 2
                elif (abs(t1 - long) < long * tol and abs(t2 - short) < short * tol):
                    bits.append(1)
                    i += 2
                else:
                    i += 1
            
            if 20 <= len(bits) <= 32:
                code = 0
                for b in bits[:24]:
                    code = (code << 1) | b
                if code > 1000:
                    return {'code': code, 'pulse': pulse_test, 'bits': len(bits)}
        
        return None


class ManchesterDecoder:
    """Manchester encoding decoder"""
    def decode(self, timings, base_pulse=189):
        if len(timings) < 40:
            return None
        
        bits = []
        for t in timings:
            if base_pulse * 0.7 < t < base_pulse * 1.5:
                bits.append('S')  # Short
            elif base_pulse * 1.8 < t < base_pulse * 3.5:
                bits.append('L')  # Long
            elif t > base_pulse * 8:
                bits.append('Y')  # Sync
        
        # Manchester: SS=0, LL=1 or similar patterns
        code_bits = []
        i = 0
        while i < len(bits) - 1:
            if bits[i:i+2] == ['S', 'S']:
                code_bits.append(0)
                i += 2
            elif bits[i:i+2] == ['L', 'L']:
                code_bits.append(1)
                i += 2
            elif bits[i] == 'S' and bits[i+1] == 'L':
                code_bits.append(0)
                i += 2
            elif bits[i] == 'L' and bits[i+1] == 'S':
                code_bits.append(1)
                i += 2
            else:
                i += 1
        
        if 20 <= len(code_bits) <= 32:
            code = 0
            for b in code_bits[:24]:
                code = (code << 1) | b
            if code > 1000:
                return {'code': code, 'bits': len(code_bits)}
        return None


class PWMDecoder:
    """PWM-based decoder - uses duty cycle"""
    def decode(self, timings):
        if len(timings) < 40:
            return None
        
        # Group into pairs and check duty cycle
        bits = []
        for i in range(0, len(timings) - 1, 2):
            high = timings[i]
            low = timings[i + 1]
            total = high + low
            
            if total < 100 or total > 5000:
                continue
            
            duty = high / total
            if duty < 0.35:
                bits.append(0)
            elif duty > 0.65:
                bits.append(1)
            # else skip (might be sync)
        
        if 20 <= len(bits) <= 32:
            code = 0
            for b in bits[:24]:
                code = (code << 1) | b
            if code > 1000:
                return {'code': code, 'bits': len(bits)}
        return None


# ============================================================
# PART 3: Run comprehensive tests
# ============================================================

results = defaultdict(list)
successful_configs = []

def test_configuration(pulse_length, protocol, decoder_name, decoder, repeats=5):
    """Test a specific configuration"""
    # Transmit
    tx_code_raw(TEST_CODE, pulse_length, protocol, repeats)
    time.sleep(0.1)
    
    # Try rpi_rf as well
    try:
        from rpi_rf import RFDevice
        tx = RFDevice(TX_PIN)
        tx.enable_tx()
        tx.tx_code(TEST_CODE, protocol, pulse_length, repeats)
        tx.cleanup()
    except:
        pass
    
    return None  # We'll check decoder separately

# Pulse lengths to try
pulse_lengths = [150, 175, 189, 200, 225, 250, 300, 350, 400, 450, 500]

# Protocols to try
protocols = [1, 2, 3, 4, 5]

log("Starting comprehensive test...")
log("=" * 70)
log("")

decoder = SimpleDecoder(tolerance=0.4)
manchester = ManchesterDecoder()
pwm_decoder = PWMDecoder()

total_tests = len(pulse_lengths) * len(protocols)
test_num = 0

for pulse in pulse_lengths:
    for proto in protocols:
        test_num += 1
        # Progress indicator (console only, not logged)
        print(f"\r[{test_num}/{total_tests}] Testing pulse={pulse}µs, protocol={proto}...", end="", flush=True)
        
        # Transmit with this configuration
        tx_code_raw(TEST_CODE, pulse, proto, repeats=8)
        
        # Small delay then capture
        time.sleep(0.05)
        
        # Capture during next transmission
        capture_thread_done = False
        captured_timings = [None]  # Use list to allow modification in nested function
        
        def capture_while_transmitting():
            captured_timings[0] = decoder.capture(duration=1.5)
        
        # Start capture
        cap_thread = threading.Thread(target=capture_while_transmitting)
        cap_thread.start()
        
        # Transmit again while capturing
        time.sleep(0.2)
        tx_code_raw(TEST_CODE, pulse, proto, repeats=15)
        
        cap_thread.join()
        
        # Get the captured timings
        timings = captured_timings[0] if captured_timings[0] else []
        
        # Try all decoders
        for dec_name, dec_func in [
            ('Simple', lambda t: decoder.decode(t, pulse)),
            ('Manchester', lambda t: manchester.decode(t, pulse)),
            ('PWM', lambda t: pwm_decoder.decode(t)),
        ]:
            result = dec_func(timings)
            if result and result['code'] > 1000:
                match = "✓ MATCH!" if result['code'] == TEST_CODE else f"got {result['code']}"
                successful_configs.append({
                    'pulse': pulse,
                    'protocol': proto,
                    'decoder': dec_name,
                    'result': result,
                    'match': result['code'] == TEST_CODE
                })
                log(f"\n   📡 {dec_name}: Code={result['code']} {match}")
        
        time.sleep(0.1)

log("\n")
log("=" * 70)
log("RESULTS SUMMARY")
log("=" * 70)

if successful_configs:
    log(f"\n✅ Found {len(successful_configs)} successful decodes!\n")
    
    # Group by match status
    matches = [c for c in successful_configs if c['match']]
    partial = [c for c in successful_configs if not c['match']]
    
    if matches:
        log("🎉 EXACT MATCHES (these configurations work!):")
        for cfg in matches:
            log(f"   Pulse: {cfg['pulse']}µs, Protocol: {cfg['protocol']}, Decoder: {cfg['decoder']}")
        
        best = matches[0]
        log(f"\n   Recommended settings for config.json:")
        log(f'   "pulse_length": {best["pulse"]},')
        log(f'   "protocol": {best["protocol"]}')
    
    if partial and not matches:
        log("⚠️  Partial decodes (got codes but not exact match):")
        for cfg in partial[:10]:
            log(f"   Pulse: {cfg['pulse']}µs, Protocol: {cfg['protocol']}, "
                  f"Decoder: {cfg['decoder']}, Got: {cfg['result']['code']}")
else:
    log("\n❌ No successful decodes with any configuration.")
    log("\n   The receiver hardware may need replacement (RXB6 recommended).")
    log("   Or try moving the receiver further from the Pi's electronics.")

# Also try rpi_rf library one more time with various settings
log("\n" + "-" * 70)
log("Bonus: Testing rpi_rf library with various pulse lengths...")

try:
    from rpi_rf import RFDevice
    
    for pulse in [150, 189, 250, 350, 500]:
        log(f"\n  Testing rpi_rf with pulse={pulse}µs...")
        
        # Setup receiver
        rx = RFDevice(RX_PIN)
        rx.enable_rx()
        
        # Transmit
        tx = RFDevice(TX_PIN)
        tx.enable_tx()
        
        for _ in range(3):
            tx.tx_code(TEST_CODE, 1, pulse, 5)
            time.sleep(0.3)
            
            if rx.rx_code and rx.rx_code > 1000:
                log(f"    📡 Received: {rx.rx_code} (pulse: {rx.rx_pulselength})")
                if rx.rx_code == TEST_CODE:
                    log(f"    🎉 MATCH!")
                rx.rx_code_timestamp = 0
        
        tx.cleanup()
        rx.cleanup()
        time.sleep(0.2)

except Exception as e:
    log(f"  rpi_rf test error: {e}")

GPIO.cleanup()

# Save all results to file
with open(LOG_FILE, 'w') as f:
    f.write('\n'.join(log_lines))

log("")
log("=" * 70)
log("Test complete!")
log(f"Full results saved to: {LOG_FILE}")
log("=" * 70)

# Final save
with open(LOG_FILE, 'w') as f:
    f.write('\n'.join(log_lines))

# ============================================================
# FINAL SUMMARY - Always shown on screen
# ============================================================
print("\n")
print("*" * 70)
print("*" + " " * 68 + "*")
print("*" + "  FINAL SUMMARY - COPY THIS TO SHARE RESULTS  ".center(68) + "*")
print("*" + " " * 68 + "*")
print("*" * 70)
print()

# Count results
total_decodes = len(successful_configs)
exact_matches = len([c for c in successful_configs if c['match']])
partial_matches = len([c for c in successful_configs if not c['match']])

print(f"📊 TEST STATISTICS:")
print(f"   Total configurations tested: {total_tests}")
print(f"   Successful decodes: {total_decodes}")
print(f"   Exact matches (code={TEST_CODE}): {exact_matches}")
print(f"   Partial matches (wrong code): {partial_matches}")
print()

if exact_matches > 0:
    print("🎉 SUCCESS! Found working configurations:")
    matches = [c for c in successful_configs if c['match']]
    for cfg in matches[:5]:  # Show top 5
        print(f"   ✓ Pulse: {cfg['pulse']}µs, Protocol: {cfg['protocol']}, Decoder: {cfg['decoder']}")
    print()
    best = matches[0]
    print(f"   📝 RECOMMENDED SETTINGS:")
    print(f"      pulse_length: {best['pulse']}")
    print(f"      protocol: {best['protocol']}")
elif partial_matches > 0:
    print("⚠️  PARTIAL SUCCESS - Decoded signals but wrong codes:")
    partials = [c for c in successful_configs if not c['match']]
    for cfg in partials[:5]:
        print(f"   • Pulse: {cfg['pulse']}µs, Got code: {cfg['result']['code']}")
    print()
    print("   This means the receiver IS working but timing needs adjustment.")
    print("   Try adjusting the tuning coil slightly more.")
else:
    print("❌ NO SUCCESSFUL DECODES")
    print()
    print("   The receiver could not decode any transmitted signals.")
    print("   Hardware recommendations:")
    print("   1. Order RXB6 superheterodyne receiver (~$3)")
    print("   2. Add 0.1µF capacitor between VCC and GND")
    print("   3. Try different GPIO pin for receiver")

print()
print("*" * 70)
print()
print(f"Full log saved to: {LOG_FILE}")
print("View with: cat ~/cherrypi/rf_test_results.txt")
