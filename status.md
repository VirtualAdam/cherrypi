# CherryPi Project Status

**Last Updated:** December 2, 2025, Late Night  
**Status:** RF Receiver DECODING WORKS ✅ - Integration with sniffer service NOT WORKING ❌

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
- **433MHz RX Module (MX-RM-5V)** - Connected to GPIO 27 (WORKING ✅)

### Software Stack
- **OS:** Debian 13 (Trixie) with kernel 6.12
- **Python:** 3.13.5 (in venv at ~/cherrypi/venv)
- **GPIO Library:** rpi-lgpio (NOT RPi.GPIO - incompatible with new kernel)
- **Docker:** Services containerized via docker-compose.yml
- **Database:** Redis for pub/sub and state management

---

## 🎉 MAJOR BREAKTHROUGH: RF Decoding Works!

We successfully decoded RF codes with **99%+ accuracy** using sync gap detection.

### Test Results (December 2, 2025)
```
Hold button on remote, then press ENTER...
Capturing for 2 seconds...
  Total transitions: 4234
  Sync gaps (>4000µs): 85
  Valid segments found: 84

✅ Codes captured:
   Code: 1334540 (seen 83x)  ← EXACT MATCH to known OFF code
   Code: 1334531 (seen 84x)  ← EXACT MATCH to known ON code
   Short: 180µs, Long: 550µs
```

### Key Algorithm Discovery
- **Sync Gap Detection:** PT2262/EV1527 remotes have ~5700µs gaps between code repeats
- **Threshold:** Pulses >4000µs mark segment boundaries
- **Pulse Timings:** Short ~180µs, Long ~550µs (ratio ~3:1)
- **Accuracy:** 99%+ (83-84 matches out of 84-85 segments)

### Working Test Script
`src/RFController/test_custom_decoder.py` - This script WORKS perfectly when run directly:
```bash
cd ~/cherrypi && source venv/bin/activate
python3 src/RFController/test_custom_decoder.py
```

---

## ❌ Current Problem: Sniffer Service Integration

The decoding algorithm works in `test_custom_decoder.py` but the web UI's "Add Switch" wizard never completes. When clicking "Start Capture" in the UI, it never times out or returns results.

### What We Know
1. `test_custom_decoder.py` works perfectly when run directly on the Pi
2. The sniffer service (`sniffer_service.py`) is triggered via Redis pub/sub
3. Something is preventing the capture from completing in the service

### Suspected Issues
1. **Docker GPIO Access** - The sniffer runs in Docker; GPIO might not be accessible
2. **Import Failure** - `custom_rf_decoder.py` imports RPi.GPIO at module level, which may fail in Docker
3. **Threading/Redis** - The sniffer runs in a background thread; something may be blocking
4. **Silent Exception** - An error might be swallowed without publishing a result

### Files Involved
- `src/RFController/sniffer_service.py` - Listens for Redis commands, runs capture
- `src/RFController/custom_rf_decoder.py` - The decoding algorithm (works standalone)
- `src/RFController/test_custom_decoder.py` - Standalone test script (WORKS ✅)

---

## Next Steps for Morning

### Priority 1: Diagnose Why Sniffer Service Fails
```bash
# On Pi - check Docker logs for errors
cd ~/cherrypi && git pull
docker compose logs rfcontroller --tail 100

# Look for:
# - "Using custom RF decoder" vs "Using rpi_rf decoder" (import issue)
# - Any exceptions or errors
# - "Sniffer finished" message (should appear after 2 seconds)
```

### Priority 2: Test If Docker Has GPIO Access
```bash
# Test if GPIO works inside the rfcontroller container
docker compose exec rfcontroller python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"
```

### Priority 3: If Docker GPIO Fails
The sniffer may need to run OUTSIDE Docker, directly on the Pi. Options:
1. Run `sniffer_service.py` as a systemd service instead of in Docker
2. Use Docker's `--privileged` flag and device mapping for GPIO
3. Check the `Dockerfile` for proper GPIO device mounting

### Priority 4: Simple Debug Test
Add logging to see what's happening:
```python
# In sniffer_service.py, add at the start of run_sniffer():
logging.info(f"RF_AVAILABLE={RF_AVAILABLE}, USE_CUSTOM_DECODER={USE_CUSTOM_DECODER}")
```

---

## Known Working Codes

| Outlet | ON Code | OFF Code |
|--------|---------|----------|
| 1 | 1332531 | 1332540 |
| 2 | 1332675 | 1332684 |
| 3 | 1332995 | 1333004 |
| 4 | 1334531 | 1334540 |
| 5 | 1340675 | 1340684 |

**Pulse Length:** ~180µs (measured), 189µs (original config)  
**Protocol:** 1

---

## Configuration Reference

### config.json Settings
```json
{
  "settings": {
    "gpio_tx_pin": 17,
    "gpio_rx_pin": 27,
    "pulse_length": 189,
    "protocol": 1,
    "sniffer_timeout": 30
  }
}
```

---

## Useful Commands

### On the Pi (SSH as awiedemann@192.168.0.199)
```bash
# Activate venv
cd ~/cherrypi && source venv/bin/activate

# Pull latest code
git pull

# Run the WORKING test script
python3 src/RFController/test_custom_decoder.py

# Check Docker services
docker compose ps
docker compose logs -f rfcontroller

# Rebuild and restart Docker
docker compose down && docker compose up -d --build
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

## Tests Status
All 15 tests passing ✅
```
test/RFController/test_controller.py - 7 tests
test/backend/test_main.py - 8 tests
```

---

## Key Files Modified Tonight

1. **`custom_rf_decoder.py`** - Rewritten with sync gap detection algorithm
2. **`sniffer_service.py`** - Simplified to use 2-second capture window (but not working in Docker)
3. **`test_custom_decoder.py`** - Restored; this is the WORKING reference implementation

---

## Summary for Next Agent

**THE DECODING ALGORITHM WORKS.** We proved it with `test_custom_decoder.py` achieving perfect code matches.

The remaining issue is getting the same algorithm to work when triggered from the web UI's "Add Switch" wizard. The sniffer service receives the command via Redis but never returns results.

Most likely cause: Docker container can't access GPIO, so the custom decoder import fails and it falls back to broken rpi_rf code, or GPIO.input() hangs.

**Start by checking Docker logs and testing GPIO access inside the container.**
