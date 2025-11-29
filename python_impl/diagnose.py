import sys
import time
import platform

print(f"Python Version: {sys.version}")
print(f"Platform: {platform.platform()}")

try:
    import RPi.GPIO as GPIO
    print(f"RPi.GPIO imported successfully. Version: {GPIO.VERSION}")
except ImportError:
    print("RPi.GPIO not found.")
except Exception as e:
    print(f"Error importing RPi.GPIO: {e}")

try:
    from rpi_rf import RFDevice
    print("rpi-rf imported successfully.")
except ImportError:
    print("rpi-rf not found.")

# Test GPIO access
GPIO_PIN = 17
print(f"\nTesting GPIO access on Pin {GPIO_PIN}...")
try:
    rfdevice = RFDevice(GPIO_PIN)
    rfdevice.enable_tx()
    print("Successfully enabled TX on GPIO 17.")
    
    print("Sending a dummy code to test execution...")
    rfdevice.tx_code(123456, 1, 189)
    print("Send complete.")
    
    rfdevice.cleanup()
    print("Cleanup complete. Library seems to be working.")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    print("If you see 'No access to /dev/mem', you need to install 'rpi-lgpio'.")
