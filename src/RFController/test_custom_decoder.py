#!/usr/bin/env python3
"""
Quick test script for the custom RF decoder.
Run this on the Pi to verify it can capture codes from the remote.

Usage:
    python3 test_custom_decoder.py

Hold a button on your remote, then press Enter.
"""

import time
import sys

# Add current directory to path
sys.path.insert(0, '.')

from custom_rf_decoder import CustomRFDecoder

def main():
    print("=" * 60)
    print("Custom RF Decoder Test")
    print("=" * 60)
    print()
    print("Calibration: 275µs short pulse, 640µs long pulse")
    print()
    
    decoder = CustomRFDecoder(gpio_pin=27)
    
    try:
        while True:
            print("-" * 40)
            input("Hold a button on your remote, then press ENTER...")
            print("Listening for 2 seconds...")
            
            result = decoder.receive(timeout=2)
            
            if result:
                print()
                print("✅ SUCCESS! Code captured:")
                print(f"   Code:         {result['code']}")
                print(f"   Pulse length: {result['pulselength']}µs")
                print(f"   Short pulse:  {result.get('short_pulse', 'N/A')}µs")
                print(f"   Long pulse:   {result.get('long_pulse', 'N/A')}µs")
                print(f"   Bits:         {result.get('bits', 'N/A')}")
            else:
                print("❌ No code received")
            
            print()
        
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    finally:
        decoder.cleanup()


if __name__ == "__main__":
    main()
