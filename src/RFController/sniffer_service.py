#!/usr/bin/env python3
"""
Sniffer Service for CherryPi RF Controller
On-demand RF code sniffing via Redis commands
"""

import redis
import json
import logging
import os
import sys
import time
import threading
from config_manager import get_settings

# Try to import custom RF decoder, then fall back to rpi_rf
try:
    from custom_rf_decoder import CustomRFDecoder
    RF_AVAILABLE = True
    USE_CUSTOM_DECODER = True
    logging.info("Using custom RF decoder (calibrated for this hardware)")
except ImportError:
    USE_CUSTOM_DECODER = False
    try:
        from rpi_rf import RFDevice
        RF_AVAILABLE = True
        logging.info("Using rpi_rf decoder")
    except ImportError:
        RF_AVAILABLE = False
        logging.warning("No RF decoder available - sniffer will run in mock mode")

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
SNIFFER_COMMANDS_CHANNEL = 'sniffer_commands'
SNIFFER_RESULTS_CHANNEL = 'sniffer_results'
SNIFFER_STATUS_KEY = 'sniffer:status'

# Sniffer state
sniffer_active = False
sniffer_thread = None
stop_sniffer = threading.Event()


def get_sniffer_gpio():
    """Get RX GPIO pin from settings"""
    settings = get_settings()
    return settings.get('gpio_rx_pin', 27)


def get_sniffer_timeout():
    """Get sniffer timeout from settings"""
    settings = get_settings()
    return settings.get('sniffer_timeout', 30)


def run_sniffer(r, request_id, capture_type):
    """
    Run the RF sniffer and capture codes.
    
    Simple flow:
    1. Capture GPIO data for exactly 2 seconds (blocking)
    2. Analyze the captured data
    3. Find the most frequent code (filters outliers)
    4. Return result
    
    No loops, no complex timeout management.
    
    Args:
        r: Redis client
        request_id: Request ID for response correlation
        capture_type: 'on' or 'off' (which button we're capturing)
    """
    global sniffer_active
    
    gpio_pin = get_sniffer_gpio()
    capture_duration = 2.0  # Fixed 2-second capture window
    
    logging.info(f"Starting sniffer on GPIO {gpio_pin} for {capture_type} button")
    
    # Update status in Redis
    r.set(SNIFFER_STATUS_KEY, json.dumps({
        'active': True,
        'request_id': request_id,
        'capture_type': capture_type,
        'started_at': time.time()
    }))
    
    # Publish starting notification
    r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
        'request_id': request_id,
        'event': 'started',
        'capture_type': capture_type,
        'message': f'Capturing for {capture_duration} seconds...'
    }))
    
    try:
        if RF_AVAILABLE and USE_CUSTOM_DECODER:
            logging.info(f"Using custom decoder - capturing for {capture_duration}s")
            
            # Create decoder and capture for exactly 2 seconds
            decoder = CustomRFDecoder(gpio_pin)
            result = decoder.capture_single_window(duration=capture_duration)
            decoder.cleanup()
            
            # Analyze result
            if result and result.get('code', 0) > 1000:
                code = result['code']
                logging.info(f"SUCCESS: Captured code {code} (seen {result.get('times_seen', 1)}x)")
                
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'captured',
                    'capture_type': capture_type,
                    'code': code,
                    'pulselength': result.get('pulselength', 180),
                    'protocol': result.get('protocol', 1),
                    'times_seen': result.get('times_seen', 1),
                    'segments_found': result.get('segments_found', 0)
                }))
            else:
                logging.warning("No valid code found in captured data")
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'no_code',
                    'capture_type': capture_type,
                    'error': 'No valid code captured. Hold the button BEFORE clicking Start.'
                }))
        
        elif RF_AVAILABLE:
            # Fallback to rpi_rf - simple 2 second capture
            logging.warning("Using rpi_rf fallback (less accurate)")
            from rpi_rf import RFDevice
            
            rfdevice = RFDevice(gpio_pin)
            rfdevice.enable_rx()
            
            # Capture for 2 seconds, take whatever code we get
            start_time = time.time()
            captured_code = None
            
            while time.time() - start_time < capture_duration:
                if rfdevice.rx_code_timestamp:
                    captured_code = {
                        'code': rfdevice.rx_code,
                        'pulselength': rfdevice.rx_pulselength,
                        'protocol': rfdevice.rx_proto
                    }
                time.sleep(0.01)
            
            rfdevice.cleanup()
            
            if captured_code and captured_code['code'] > 1000:
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'captured',
                    'capture_type': capture_type,
                    'code': captured_code['code'],
                    'pulselength': captured_code['pulselength'],
                    'protocol': captured_code['protocol']
                }))
            else:
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'no_code',
                    'capture_type': capture_type,
                    'error': 'No valid code captured with rpi_rf fallback.'
                }))
        
        else:
            # Mock mode for testing
            logging.info("Mock mode - simulating 2 second capture")
            time.sleep(capture_duration)
            
            mock_code = 1234567 if capture_type == 'on' else 1234568
            r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                'request_id': request_id,
                'event': 'captured',
                'capture_type': capture_type,
                'code': mock_code,
                'pulselength': 180,
                'protocol': 1,
                'mock': True
            }))
                
    except Exception as e:
        logging.exception(f"Sniffer error: {e}")
        r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
            'request_id': request_id,
            'event': 'error',
            'capture_type': capture_type,
            'error': str(e)
        }))
    
    finally:
        sniffer_active = False
        r.set(SNIFFER_STATUS_KEY, json.dumps({'active': False}))
        stop_sniffer.clear()
        logging.info("Sniffer finished")


def handle_command(r, message):
    """Process a sniffer command"""
    global sniffer_active, sniffer_thread
    
    try:
        data = json.loads(message)
        action = data.get('action')
        request_id = data.get('request_id', 'unknown')
        
        logging.info(f"Processing sniffer command: {action} (request_id: {request_id})")
        
        if action == 'start':
            if sniffer_active:
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'error',
                    'error': 'Sniffer is already running'
                }))
                return
            
            capture_type = data.get('capture_type', 'on')
            sniffer_active = True
            stop_sniffer.clear()
            
            # Start sniffer in background thread
            sniffer_thread = threading.Thread(
                target=run_sniffer,
                args=(r, request_id, capture_type),
                daemon=True
            )
            sniffer_thread.start()
            
        elif action == 'stop':
            if sniffer_active:
                stop_sniffer.set()
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'stopped',
                    'message': 'Sniffer stopped by user'
                }))
            else:
                r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                    'request_id': request_id,
                    'event': 'info',
                    'message': 'Sniffer was not running'
                }))
                
        elif action == 'status':
            status_data = r.get(SNIFFER_STATUS_KEY)
            if status_data:
                status = json.loads(status_data)
            else:
                status = {'active': False}
            
            r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                'request_id': request_id,
                'event': 'status',
                **status
            }))
            
        else:
            r.publish(SNIFFER_RESULTS_CHANNEL, json.dumps({
                'request_id': request_id,
                'event': 'error',
                'error': f'Unknown action: {action}'
            }))
            
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON: {message}")
    except Exception as e:
        logging.exception(f"Error handling sniffer command: {e}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [SnifferService] %(message)s'
    )
    
    if not RF_AVAILABLE:
        logging.warning("rpi_rf not available - running in mock mode for testing")
    
    logging.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            r.ping()
            logging.info("Connected to Redis.")
            
            # Initialize status
            r.set(SNIFFER_STATUS_KEY, json.dumps({'active': False}))
            
            pubsub = r.pubsub()
            pubsub.subscribe(SNIFFER_COMMANDS_CHANNEL)
            
            logging.info(f"Listening for sniffer commands on channel: '{SNIFFER_COMMANDS_CHANNEL}'")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    handle_command(r, message['data'])
                    
        except redis.ConnectionError as e:
            logging.error(f"Redis connection error: {e}")
            logging.info("Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.exception(f"Unexpected error: {e}")
            time.sleep(5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Sniffer service stopped.")
        sys.exit(0)
