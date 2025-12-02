#!/usr/bin/env python3
"""
Config Listener for CherryPi RF Controller
Listens to config_commands channel and processes CRUD operations
"""

import redis
import json
import logging
import os
import sys
import time
from config_manager import (
    get_switches, get_switch, add_switch, update_switch, delete_switch,
    get_settings, update_settings, sync_to_redis, get_next_id
)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
CONFIG_COMMANDS_CHANNEL = 'config_commands'
CONFIG_RESPONSES_CHANNEL = 'config_responses'


def handle_command(r, message):
    """Process a config command and publish response"""
    try:
        data = json.loads(message)
        action = data.get('action')
        request_id = data.get('request_id', 'unknown')
        payload = data.get('data', {})
        
        logging.info(f"Processing config command: {action} (request_id: {request_id})")
        
        response = {
            'request_id': request_id,
            'action': action,
            'success': True,
            'data': None,
            'error': None
        }
        
        try:
            if action == 'get_switches':
                response['data'] = get_switches()
                
            elif action == 'get_switch':
                switch_id = payload.get('id')
                switch = get_switch(switch_id)
                if switch:
                    response['data'] = switch
                else:
                    response['success'] = False
                    response['error'] = f"Switch {switch_id} not found"
                    
            elif action == 'add_switch':
                name = payload.get('name')
                on_code = payload.get('on_code')
                off_code = payload.get('off_code')
                switch_id = payload.get('id')  # Optional
                
                if not all([name, on_code, off_code]):
                    response['success'] = False
                    response['error'] = "Missing required fields: name, on_code, off_code"
                else:
                    new_switch = add_switch(name, on_code, off_code, switch_id)
                    response['data'] = new_switch
                    
            elif action == 'update_switch':
                switch_id = payload.get('id')
                if not switch_id:
                    response['success'] = False
                    response['error'] = "Missing switch ID"
                else:
                    updated = update_switch(
                        switch_id,
                        name=payload.get('name'),
                        on_code=payload.get('on_code'),
                        off_code=payload.get('off_code')
                    )
                    response['data'] = updated
                    
            elif action == 'delete_switch':
                switch_id = payload.get('id')
                if not switch_id:
                    response['success'] = False
                    response['error'] = "Missing switch ID"
                else:
                    delete_switch(switch_id)
                    response['data'] = {'deleted': switch_id}
                    
            elif action == 'get_settings':
                response['data'] = get_settings()
                
            elif action == 'update_settings':
                updated = update_settings(payload)
                response['data'] = updated
                
            elif action == 'get_next_id':
                response['data'] = {'next_id': get_next_id()}
                
            elif action == 'sync':
                sync_to_redis()
                response['data'] = {'synced': True}
                
            else:
                response['success'] = False
                response['error'] = f"Unknown action: {action}"
                
        except ValueError as ve:
            response['success'] = False
            response['error'] = str(ve)
        except Exception as e:
            response['success'] = False
            response['error'] = f"Internal error: {str(e)}"
            logging.exception(f"Error processing command {action}")
        
        # Publish response
        r.publish(CONFIG_RESPONSES_CHANNEL, json.dumps(response))
        logging.info(f"Published response for {action}: success={response['success']}")
        
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON: {message}")
    except Exception as e:
        logging.exception(f"Unexpected error handling command: {e}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [ConfigListener] %(message)s'
    )
    
    logging.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    
    # Initial sync to Redis
    logging.info("Performing initial config sync to Redis...")
    sync_to_redis()
    
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            r.ping()
            logging.info("Connected to Redis.")
            
            pubsub = r.pubsub()
            pubsub.subscribe(CONFIG_COMMANDS_CHANNEL)
            
            logging.info(f"Listening for config commands on channel: '{CONFIG_COMMANDS_CHANNEL}'")
            
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
        logging.info("Config listener stopped.")
        sys.exit(0)
