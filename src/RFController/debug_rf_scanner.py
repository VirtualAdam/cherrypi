#!/usr/bin/env python3
"""
RF Scanner Debug Tool for CherryPi
Run this directly on your Raspberry Pi to debug RF receiver hardware.

Usage:
    python debug_rf_scanner.py          # Use default GPIO 27
    python debug_rf_scanner.py -g 22    # Use GPIO 22
    python debug_rf_scanner.py --test-gpio  # Test GPIO connectivity
"""

import argparse
import logging
import sys
import time

# Setup logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_gpio_available():
    """Check if GPIO libraries are available"""
    logger.info("Checking GPIO availability...")
    
    try:
        import RPi.GPIO as GPIO
        logger.info("✅ RPi.GPIO is available")
        
        # Get Pi info
        info = GPIO.RPI_INFO
        logger.info(f"   Pi Revision: {info.get('REVISION', 'unknown')}")
        logger.info(f"   Pi Type: {info.get('TYPE', 'unknown')}")
        logger.info(f"   Pi Processor: {info.get('PROCESSOR', 'unknown')}")
        logger.info(f"   Pi RAM: {info.get('RAM', 'unknown')}")
        
        return True
    except ImportError as e:
        logger.error(f"❌ RPi.GPIO not available: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error checking GPIO: {e}")
        return False


def check_rpi_rf_available():
    """Check if rpi_rf library is available"""
    logger.info("Checking rpi_rf availability...")
    
    try:
        from rpi_rf import RFDevice
        logger.info("✅ rpi_rf is available")
        return True
    except ImportError as e:
        logger.error(f"❌ rpi_rf not available: {e}")
        logger.info("   Install with: pip install rpi-rf")
        return False


def test_gpio_pin(gpio_pin):
    """Test if a GPIO pin is accessible"""
    logger.info(f"Testing GPIO pin {gpio_pin}...")
    
    try:
        import RPi.GPIO as GPIO
        
        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Try to set up the pin as input
        GPIO.setup(gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Read initial state
        state = GPIO.input(gpio_pin)
        logger.info(f"✅ GPIO {gpio_pin} is accessible")
        logger.info(f"   Current state: {'HIGH' if state else 'LOW'}")
        
        # Monitor for a few seconds
        logger.info(f"   Monitoring pin for 3 seconds...")
        changes = 0
        last_state = state
        start = time.time()
        
        while time.time() - start < 3:
            current = GPIO.input(gpio_pin)
            if current != last_state:
                changes += 1
                last_state = current
            time.sleep(0.001)
        
        if changes > 0:
            logger.info(f"   ✅ Detected {changes} state changes - pin appears active!")
        else:
            logger.warning(f"   ⚠️ No state changes detected - check wiring")
        
        GPIO.cleanup(gpio_pin)
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing GPIO {gpio_pin}: {e}")
        return False


def print_wiring_diagram():
    """Print RF receiver wiring instructions"""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                    RF 433MHz RECEIVER WIRING                        ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  RF Receiver Module (common pinout):                                ║
║  ┌─────────────────────────────────┐                                ║
║  │  [ANT]  [VCC]  [DATA]  [GND]    │  (4-pin module)                ║
║  │    │      │      │       │      │                                ║
║  └────┼──────┼──────┼───────┼──────┘                                ║
║       │      │      │       │                                       ║
║       │      │      │       └──────► Pi Pin 6 (GND)                 ║
║       │      │      └──────────────► Pi GPIO 27 (Pin 13) *DEFAULT*  ║
║       │      └─────────────────────► Pi Pin 2 or 4 (5V)             ║
║       └────────────────────────────► Antenna (17cm wire)            ║
║                                                                      ║
╠════════════════════════════════════════════════════════════════════╣
║                     RASPBERRY PI GPIO HEADER                        ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║         3.3V  (1) (2)  5V  ◄── VCC                                  ║
║       GPIO 2  (3) (4)  5V                                           ║
║       GPIO 3  (5) (6)  GND ◄── GND                                  ║
║       GPIO 4  (7) (8)  GPIO 14                                      ║
║          GND  (9) (10) GPIO 15                                      ║
║      GPIO 17 (11) (12) GPIO 18                                      ║
║  ►►  GPIO 27 (13) (14) GND   ◄◄ DATA (default RX pin)               ║
║      GPIO 22 (15) (16) GPIO 23                                      ║
║         3.3V (17) (18) GPIO 24                                      ║
║      GPIO 10 (19) (20) GND                                          ║
║       GPIO 9 (21) (22) GPIO 25                                      ║
║      GPIO 11 (23) (24) GPIO 8                                       ║
║          GND (25) (26) GPIO 7                                       ║
║                                                                      ║
╠════════════════════════════════════════════════════════════════════╣
║  CURRENT CONFIG: RX on GPIO 27 (Pin 13), TX on GPIO 17 (Pin 11)    ║
╚════════════════════════════════════════════════════════════════════╝
""")


def run_rf_sniffer(gpio_pin, duration=None):
    """Run the RF sniffer"""
    logger.info(f"Starting RF sniffer on GPIO {gpio_pin}")
    
    try:
        from rpi_rf import RFDevice
        
        rfdevice = RFDevice(gpio_pin)
        rfdevice.enable_rx()
        
        logger.info(f"✅ RF receiver enabled on GPIO {gpio_pin}")
        logger.info("Listening for RF codes... Press Ctrl+C to stop")
        logger.info("-" * 50)
        
        timestamp = None
        codes_received = 0
        start_time = time.time()
        
        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    logger.info(f"Timeout after {duration} seconds")
                    break
                    
                if rfdevice.rx_code_timestamp != timestamp:
                    timestamp = rfdevice.rx_code_timestamp
                    codes_received += 1
                    
                    code = rfdevice.rx_code
                    pulselength = rfdevice.rx_pulselength
                    protocol = rfdevice.rx_proto
                    
                    logger.info(f"🔴 CODE RECEIVED #{codes_received}")
                    logger.info(f"   Code:        {code}")
                    logger.info(f"   Pulselength: {pulselength}")
                    logger.info(f"   Protocol:    {protocol}")
                    logger.info("-" * 50)
                    
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("\nStopped by user")
        finally:
            rfdevice.cleanup()
            logger.info(f"Total codes received: {codes_received}")
            
    except Exception as e:
        logger.error(f"❌ Error running sniffer: {e}")
        raise


def run_diagnostics(gpio_pin):
    """Run full diagnostics"""
    print("\n" + "=" * 60)
    print("         RF SCANNER DIAGNOSTICS")
    print("=" * 60 + "\n")
    
    # Check GPIO
    gpio_ok = check_gpio_available()
    print()
    
    # Check rpi_rf
    rf_ok = check_rpi_rf_available()
    print()
    
    if gpio_ok:
        # Test the specific pin
        test_gpio_pin(gpio_pin)
        print()
    
    # Print wiring diagram
    print_wiring_diagram()
    
    # Summary
    print("\n" + "=" * 60)
    print("         DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if gpio_ok and rf_ok:
        print("✅ All libraries available")
        print(f"✅ Ready to scan on GPIO {gpio_pin}")
        print("\nTo start scanning, run:")
        print(f"   python debug_rf_scanner.py -g {gpio_pin}")
    else:
        print("❌ Some issues detected - check above for details")


def main():
    parser = argparse.ArgumentParser(
        description='RF Scanner Debug Tool for CherryPi',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python debug_rf_scanner.py                    # Run sniffer on default GPIO 27
  python debug_rf_scanner.py -g 22              # Run sniffer on GPIO 22
  python debug_rf_scanner.py --diagnose         # Run full diagnostics
  python debug_rf_scanner.py --test-gpio        # Test GPIO pin only
  python debug_rf_scanner.py --wiring           # Show wiring diagram
  python debug_rf_scanner.py --timeout 30       # Stop after 30 seconds
        """
    )
    
    parser.add_argument('-g', '--gpio', type=int, default=27,
                        help='GPIO pin for RF receiver DATA (default: 27)')
    parser.add_argument('--diagnose', action='store_true',
                        help='Run full diagnostics')
    parser.add_argument('--test-gpio', action='store_true',
                        help='Test GPIO pin connectivity only')
    parser.add_argument('--wiring', action='store_true',
                        help='Show wiring diagram')
    parser.add_argument('--timeout', type=int, default=None,
                        help='Stop after N seconds (default: run until Ctrl+C)')
    
    args = parser.parse_args()
    
    if args.wiring:
        print_wiring_diagram()
        return
    
    if args.diagnose:
        run_diagnostics(args.gpio)
        return
    
    if args.test_gpio:
        check_gpio_available()
        test_gpio_pin(args.gpio)
        return
    
    # Default: run the sniffer
    check_gpio_available()
    check_rpi_rf_available()
    print()
    run_rf_sniffer(args.gpio, args.timeout)


if __name__ == '__main__':
    main()
