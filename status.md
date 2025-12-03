# CherryPi Project Status

**Last Updated:** December 2, 2025, Evening  
**Status:** RF Receiver debugging in progress - close to solution

---

## Project Architecture

### Overview
CherryPi is a home automation system for controlling 433MHz RF outlet switches via a web interface. It runs on a Raspberry Pi 4 (hostname: "baymax", IP: 192.168.0.199).

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Web UI  │────▶│  FastAPI Backend │────▶│      Redis      │
│   (port 3000)   │     │   (port 8000)    │     │   (port 6379)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                    ┌────────────────────┴────────────────────┐
                                    │                                         │
                              ┌─────▼─────┐                           ┌───────▼───────┐
                              │ controller │                           │ sniffer_service│
                              │ (TX only)  │                           │  (RX - WIP)    │
                              └─────┬─────┘                           └───────┬───────┘
                                    │                                         │
                              ┌─────▼─────┐                           ┌───────▼───────┐
                              │  GPIO 17  │                           │    GPIO 27    │
                              │ TX Module │                           │   RX Module   │
                              └───────────┘                           └───────────────┘
```

### Hardware
- **Raspberry Pi 4 Model B** - Debian 13 (Trixie), Python 3.13.5
- **433MHz TX Module** - Connected to GPIO 17 (WORKING ✅)
- **433MHz RX Module (MX-RM-5V)** - Connected to GPIO 27 (debugging)

### Software Stack
- **OS:** Debian 13 (Trixie) with kernel 6.12
- **Python:** 3.13.5 (in venv at ~/cherrypi/venv)
- **GPIO Library:** rpi-lgpio (NOT RPi.GPIO - incompatible with new kernel)
- **Docker:** Services containerized via docker-compose.yml
- **Database:** Redis for pub/sub and state management

### Key Files
- `src/RFController/config.json` - Switch configuration and RF settings
- `src/RFController/controller.py` - TX controller (sends codes)
- `src/RFController/sniffer_service.py` - RX sniffer (captures codes from remotes)
- `src/RFController/custom_rf_decoder.py` - NEW: Custom decoder (bypasses rpi_rf)
- `src/RFController/config_manager.py` - Configuration CRUD operations
- `src/backend/main.py` - FastAPI REST API
- `src/frontend/` - React web application

---

## Current Task: RF Receiver Debugging

### Goal
Enable the "Add Switch" wizard in the web UI to capture RF codes from physical remotes by sniffing their 433MHz transmissions.

### What's Working ✅
1. **TX (Transmitting)** - Completely working. Can control existing outlets.
2. **GPIO Detection** - RX module IS detecting signals (3500+ transitions in 2 seconds)
3. **Hardware Wiring** - Confirmed correct:
   - VCC → 5V (Pin 2)
   - GND → Ground (Pin 6)  
   - DATA → GPIO 27 (Pin 13)

### The Problem
The receiver captures data but decoding fails. We're getting ~1700 transitions per second even when pressing the remote button, mixing signal with noise.

---

## Debugging History (DO NOT REPEAT THESE)

### ❌ Failed Approach 1: rpi_rf Library
- **What:** Used standard `rpi_rf` library with `RFDevice(27).enable_rx()`
- **Result:** Decoded garbage codes (4, 5, 8, 262144) instead of actual codes like 1332531
- **Why it failed:** rpi_rf doesn't work properly with Python 3.13 + rpi-lgpio combination
- **Files:** Original `sniffer_service.py` used this

### ❌ Failed Approach 2: Simple GPIO Polling
- **What:** Basic polling loop checking `GPIO.input(27)` for transitions
- **Result:** Captured transitions but couldn't decode - too much noise mixed with signal
- **Files:** Early versions of debug scripts

### ❌ Failed Approach 3: Edge Detection with Callbacks
- **What:** Used `GPIO.add_event_detect()` with callbacks
- **Result:** Callback approach had timing issues, missed pulses
- **Why:** Python callback overhead too slow for µs-level timing

### ⚠️ Partial Success: Bit-by-Bit Analysis (debug_calibration.py)
- **What:** Captured raw timings, analyzed pulse durations, decoded bit by bit
- **Result:** ACHIEVED PERFECT 24/24 BIT MATCH on one test!
- **Key Discovery:** 
  - Short pulse: **275µs** (not 189µs as originally configured)
  - Long pulse: **640µs**
  - Ratio: **~2.33** (close to protocol 2's 1:2 ratio)
- **Problem:** Only worked in controlled test, not in continuous sniffer mode
- **File:** `debug_calibration.py` on the Pi (not in repo)

### ❌ Failed Approach 4: CustomRFDecoder Class
- **What:** Created `custom_rf_decoder.py` based on calibration findings
- **Result:** `receive()` method returns None - can't find valid codes in noise
- **Why:** Continuous capture mixes noise with signal, can't isolate code segments

### 🔄 Current Approach: Sync Gap Detection (IN PROGRESS)
- **What:** Look for sync gaps (>4000µs) to identify where code transmissions start
- **Status:** Code written but not yet tested
- **File:** `test_custom_decoder.py` (updated but not pushed)
- **Theory:** PT2262/EV1527 protocols have a long sync pulse between code repeats

---

## Latest Test Results (December 2, 2025 Evening)

```
Capturing for 2 seconds...
  Captured 3605 transitions
  Short pulses (150-450µs): 1793
  Long pulses (450-1200µs): 1721
❌ Could not decode a valid code
```

**Analysis:**
- GPIO IS receiving data (3605 transitions = healthy signal)
- Roughly 50/50 split of short/long pulses suggests valid RF encoding
- Problem: Can't separate signal from background noise
- Need: Sync gap detection to find code boundaries

---

## Unpushed Changes

The following changes are in the local repo but may not be pushed:

1. **`test_custom_decoder.py`** - Updated with sync gap detection logic
   - Looks for pulses >4000µs as segment boundaries
   - Decodes each segment separately
   - Counts how many times each code appears

To push these changes:
```powershell
cd C:\Users\awiedemann\Projects\CherryPi
git add -A
git commit -m "Add sync gap detection to find code segments"
git push
```

---

## Next Steps (Morning)

### Priority 1: Push and Test Sync Gap Detection
```powershell
# On Windows - push the changes
cd C:\Users\awiedemann\Projects\CherryPi
git add -A; git commit -m "Add sync gap detection"; git push
```

```bash
# On Pi - pull and test
cd ~/cherrypi && git pull
source venv/bin/activate
python3 src/RFController/test_custom_decoder.py
```
Check if sync gaps are being detected and if segments decode properly.

### Priority 2: If Sync Detection Fails
Try lowering the sync gap threshold or analyze the raw timing data:
- Print first 100 pulse durations to see the pattern
- Look for any pulses >2000µs that could be sync markers
- The remote likely sends the code 4-8 times in rapid succession

### Priority 3: Alternative - Hardware Noise Reduction
If software decoding continues to fail:
- Add 0.1µF capacitor between VCC and GND on receiver
- Try different antenna length (17.3cm is ideal for 433MHz)
- Move receiver away from Pi (EMI from Pi can cause noise)

### Priority 4: Once Decoding Works
1. Update `custom_rf_decoder.py` with working algorithm
2. Update `sniffer_service.py` to use custom decoder
3. Test end-to-end: Web UI → Start Sniffer → Capture Code → Save Switch

---

## Configuration Reference

### config.json Settings (Current)
```json
{
  "settings": {
    "gpio_tx_pin": 17,
    "gpio_rx_pin": 27,
    "pulse_length": 275,
    "protocol": 1,
    "sniffer_timeout": 30
  }
}
```

### Known Working Code (for testing)
- **Code:** 1332531 (from existing remote)
- **Pulse Length:** 275µs (calibrated)
- **Protocol:** 1 (but ratio suggests protocol 2 might work too)

---

## Useful Commands

### On the Pi (SSH as awiedemann@192.168.0.199)
```bash
# Activate venv
cd ~/cherrypi && source venv/bin/activate

# Run test script
python3 src/RFController/test_custom_decoder.py

# Check Docker services
docker compose ps
docker compose logs -f

# GPIO info
pinout
gpio readall
```

### On Windows Dev Machine
```powershell
# Run tests
cd C:\Users\awiedemann\Projects\CherryPi
python -m pytest test/ -v

# Push to Pi
git add -A; git commit -m "message"; git push
```

---

## Debug Scripts on Pi (Not in Repo)

These were created during debugging and exist only on the Pi in ~/cherrypi or ~/:
- `debug_receiver.py` - Basic GPIO test
- `debug_gpio_raw.py` - Raw transition counter
- `debug_signal_analysis.py` - Timing histogram
- `debug_protocol_test.py` - Protocol comparison
- `debug_self_test.py` - TX→RX loopback test (PASSED)
- `debug_tuning.py` - Noise level measurement
- `debug_custom_decoder.py` - Custom decode attempts
- `debug_ultimate_test.py` - Comprehensive test
- `debug_calibration.py` - **THIS ONE GOT PERFECT MATCH** ⭐

---

## Key Insight for Next Agent

The receiver DOES work. We proved it with `debug_calibration.py` achieving a perfect 24/24 bit match. The challenge is that:

1. There's constant background noise (~145 transitions/sec even with no remote)
2. When button is pressed, signal mixes with noise (~1700+ transitions/sec)
3. Need to find sync gaps or use statistical methods to extract valid codes

The sync gap approach in the updated `test_custom_decoder.py` is the most promising next step. PT2262 remotes typically have a sync pulse of ~31× the short pulse length (275µs × 31 ≈ 8500µs), so looking for gaps >4000µs should isolate code segments.

---

## Tests Status
All 15 tests passing ✅
```
test/RFController/test_controller.py - 7 tests
test/backend/test_main.py - 8 tests
```
