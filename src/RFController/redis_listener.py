#!/usr/bin/env python3

import redis
import json
import logging
import os
import time
from controller import control_outlet

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_CHANNEL = 'rf_commands'

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [RedisListener] %(message)s')
    
    logging.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            # Test connection
            r.ping()
            logging.info("Connected to Redis.")
            
            pubsub = r.pubsub()
            pubsub.subscribe(REDIS_CHANNEL)
            
            logging.info(f"Listening for events on channel: '{REDIS_CHANNEL}'")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        payload = message['data']
                        logging.info(f"Received message: {payload}")
                        
                        data = json.loads(payload)
                        outlet_id = int(data.get('outlet'))
                        state = data.get('state')
                        
                        if outlet_id and state:
                            control_outlet(outlet_id, state)
                        else:
                            logging.warning(f"Invalid message format. Expected 'outlet' and 'state'. Got: {data}")
                            
                    except json.JSONDecodeError:
                        logging.error(f"Failed to decode JSON: {message['data']}")
                    except ValueError as ve:
                        logging.error(f"Value error (invalid outlet ID?): {ve}")
                    except Exception as e:
                        logging.error(f"Error processing message: {e}")
                        
        except redis.ConnectionError:
            logging.error(f"Lost connection to Redis at {REDIS_HOST}:{REDIS_PORT}. Retrying in 5 seconds...")
            time.sleep(5)
        except KeyboardInterrupt:
            logging.info("Stopping listener...")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    main()
