#!/usr/bin/env python3
"""
Simple test script to publish a switch command via Redis.
This tests the full stack: Redis -> controller -> RF transmit
"""

import redis
import json
import sys
import os

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
COMMANDS_CHANNEL = 'rf_commands'

def send_command(switch_id: int, state: str):
    """Publish a switch command to Redis"""
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    # Match the format expected by redis_listener.py
    command = {
        'outlet': switch_id,
        'state': state  # 'on' or 'off'
    }
    
    print(f"Publishing to '{COMMANDS_CHANNEL}':")
    print(f"  {json.dumps(command, indent=2)}")
    
    result = r.publish(COMMANDS_CHANNEL, json.dumps(command))
    print(f"  Subscribers received: {result}")
    
    if result == 0:
        print("\n⚠️  No subscribers! Make sure the controller is running:")
        print("    python3 src/RFController/main.py")
    else:
        print("\n✅ Command sent!")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 test_redis_tx.py <switch_id> <on|off>")
        print()
        print("Examples:")
        print("  python3 test_redis_tx.py 1 on   # Turn switch 1 ON")
        print("  python3 test_redis_tx.py 1 off  # Turn switch 1 OFF")
        sys.exit(1)
    
    switch_id = int(sys.argv[1])
    state = sys.argv[2].lower()
    
    if state not in ['on', 'off']:
        print("Error: state must be 'on' or 'off'")
        sys.exit(1)
    
    send_command(switch_id, state)

if __name__ == '__main__':
    main()
