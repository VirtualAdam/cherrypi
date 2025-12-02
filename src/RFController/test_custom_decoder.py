#!/usr/bin/env python3
"""
Quick test script for the custom RF decoder.
Run this on the Pi to verify it can capture codes from the remote.

Usage:
    python3 test_custom_decoder.py

Press a button on your remote within 30 seconds.
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
    print("This test will listen for RF codes using our calibrated decoder.")
    print("Calibration: 275µs short pulse, 640µs long pulse")
    print()
    print("Press a button on your remote...")
    print()
    
    decoder = CustomRFDecoder(gpio_pin=27)
    
    try:
        # Try to receive up to 5 codes
        for i in range(5):
            print(f"[Attempt {i+1}/5] Listening for 30 seconds...")
            
            result = decoder.receive(timeout=30)
            
            if result:
                print()
                print("✅ SUCCESS! Code captured:")
                print(f"   Code:         {result['code']}")
                print(f"   Pulse length: {result['pulselength']}µs")
                print(f"   Short pulse:  {result.get('short_pulse', 'N/A')}µs")
                print(f"   Long pulse:   {result.get('long_pulse', 'N/A')}µs")
                print(f"   Bits:         {result.get('bits', 'N/A')}")
                print()
                
                # Ask to continue
                try:
                    cont = input("Press another button? (y/n): ").strip().lower()
                    if cont != 'y':
                        break
                    print()
                except EOFError:
                    break
            else:
                print("   No code received (timeout)")
                print()
        
        print("Test complete!")
        
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        decoder.cleanup()


if __name__ == "__main__":
    main()
