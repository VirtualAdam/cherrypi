#!/usr/bin/env python3
"""
Quick test script for the custom RF decoder.
Uses sync gap detection and clear error reporting.
"""

import time
import sys
import os

# Add parent directory to path so we can import the custom_rf_decoder module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from custom_rf_decoder import CustomRFDecoder, RFDecodeError

GPIO_PIN = 27


def main():
    print("=" * 60)
    print("Custom RF Decoder Test - Sync Gap Detection")
    print("=" * 60)
    print(f"GPIO Pin: {GPIO_PIN}")
    print()
    print("This test captures for 2 seconds and analyzes the signal.")
    print("It will give you a clear result: SUCCESS or a specific error.")
    print()
    
    decoder = CustomRFDecoder(gpio_pin=GPIO_PIN)
    
    try:
        while True:
            print("-" * 60)
            input("Hold button on remote, then press ENTER...")
            print("Capturing for 2 seconds...")
            print()
            
            try:
                # Use the improved capture method with clear error handling
                result = decoder.capture_single_window(duration=2.0, min_confidence=0.5, min_segments=3)
                
                # SUCCESS!
                print("✅ SUCCESS! Code captured clearly.")
                print()
                print(f"   Code:         {result['code']}")
                print(f"   Pulse length: {result['pulselength']}µs")
                print(f"   Short pulse:  {result['short_pulse']}µs")
                print(f"   Long pulse:   {result['long_pulse']}µs")
                print(f"   Protocol:     {result['protocol']}")
                print()
                print(f"   Confidence:   {result['confidence']*100:.0f}%")
                print(f"   Times seen:   {result['times_seen']}x out of {result['segments_found']} segments")
                print(f"   Unique codes: {result['total_codes_found']}")
                print(f"   Success rate: {result['decode_success_rate']}%")
                
            except RFDecodeError as e:
                # Clear, specific error
                print(f"❌ {e.error_type}: {e.message}")
                print()
                print("   Details:")
                for key, value in e.details.items():
                    if key == "competing_codes":
                        print(f"     {key}:")
                        for cc in value:
                            print(f"       - Code {cc['code']}: {cc['count']}x ({cc['percentage']}%)")
                    elif key == "suggestion":
                        print()
                        print(f"   💡 {value}")
                    else:
                        print(f"     {key}: {value}")
            
            print()
        
    except KeyboardInterrupt:
        print("\n\nStopped by user (Ctrl+C)")
    finally:
        decoder.cleanup()


if __name__ == "__main__":
    main()
