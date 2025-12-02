#!/usr/bin/env python3
"""
Main entry point for CherryPi RF Controller
Runs all services: redis_listener, config_listener, sniffer_service
"""

import subprocess
import sys
import signal
import logging
import time

processes = []


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logging.info("Shutting down all services...")
    for proc in processes:
        if proc.poll() is None:  # Process is still running
            proc.terminate()
    
    # Wait for processes to terminate
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    
    logging.info("All services stopped.")
    sys.exit(0)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [Main] %(message)s'
    )
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    services = [
        ('Redis Listener', ['python', 'redis_listener.py']),
        ('Config Listener', ['python', 'config_listener.py']),
        ('Sniffer Service', ['python', 'sniffer_service.py']),
    ]
    
    logging.info("Starting CherryPi RF Controller services...")
    
    for name, cmd in services:
        logging.info(f"Starting {name}...")
        proc = subprocess.Popen(
            cmd,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(proc)
        time.sleep(0.5)  # Small delay between service starts
    
    logging.info(f"All {len(services)} services started.")
    
    # Monitor processes
    while True:
        for i, (name, _) in enumerate(services):
            proc = processes[i]
            if proc.poll() is not None:
                logging.error(f"{name} exited with code {proc.returncode}")
                # Could add restart logic here if needed
        time.sleep(5)


if __name__ == '__main__':
    main()
