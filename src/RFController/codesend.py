#!/usr/bin/env python3

import argparse
import logging
import sys
import time
from rpi_rf import RFDevice

def main():
    parser = argparse.ArgumentParser(description='Sends a decimal code via a 433/315MHz GPIO device')
    parser.add_argument('code', metavar='CODE', type=int,
                        help="Decimal code to send")
    parser.add_argument('-g', '--gpio', dest='gpio', type=int, default=17,
                        help="GPIO pin (Default: 17)")
    parser.add_argument('-p', '--pulselength', dest='pulselength', type=int, default=189,
                        help="Pulse length (Default: 189)")
    parser.add_argument('-t', '--protocol', dest='protocol', type=int, default=1,
                        help="Protocol (Default: 1)")
    args = parser.parse_args()

    rfdevice = RFDevice(args.gpio)
    rfdevice.enable_tx()
    
    logging.info(f"Sending code: {args.code} [protocol: {args.protocol}, pulselength: {args.pulselength}]")
    rfdevice.tx_code(args.code, args.protocol, args.pulselength)
    rfdevice.cleanup()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', )
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
