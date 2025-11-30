#!/usr/bin/env python3

import argparse
import logging
import sys
import time
from rpi_rf import RFDevice

def main():
    parser = argparse.ArgumentParser(description='Receives a decimal code via a 433/315MHz GPIO device')
    parser.add_argument('-g', '--gpio', dest='gpio', type=int, default=27,
                        help="GPIO pin (Default: 27)")
    args = parser.parse_args()

    rfdevice = RFDevice(args.gpio)
    rfdevice.enable_rx()
    timestamp = None
    logging.info(f"Listening for codes on GPIO {args.gpio}")

    try:
        while True:
            if rfdevice.rx_code_timestamp != timestamp:
                timestamp = rfdevice.rx_code_timestamp
                logging.info(f"Received code: {rfdevice.rx_code} [pulselength {rfdevice.rx_pulselength}, protocol {rfdevice.rx_proto}]")
            time.sleep(0.01)
    finally:
        rfdevice.cleanup()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', )
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
