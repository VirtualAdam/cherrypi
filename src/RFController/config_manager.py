#!/usr/bin/env python3
"""
Config Manager for CherryPi RF Controller
Handles CRUD operations for switches and syncs to Redis
"""

import json
import os
import logging
import threading
import redis

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_CONFIG_KEY = 'config:switches'
REDIS_SETTINGS_KEY = 'config:settings'

_lock = threading.Lock()
_config_cache = None


def get_redis_client():
    """Get Redis client connection"""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def load_config():
    """Load configuration from file"""
    global _config_cache
    with _lock:
        try:
            with open(CONFIG_FILE, 'r') as f:
                _config_cache = json.load(f)
            return _config_cache
        except FileNotFoundError:
            logging.warning(f"Config file not found, creating default: {CONFIG_FILE}")
            _config_cache = {"switches": [], "settings": get_default_settings()}
            save_config(_config_cache)
            return _config_cache
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in config file: {e}")
            raise


def save_config(config):
    """Save configuration to file"""
    global _config_cache
    with _lock:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        _config_cache = config
    logging.info("Config saved to file")


def get_default_settings():
    """Return default settings"""
    return {
        "gpio_tx_pin": 17,
        "gpio_rx_pin": 27,
        "pulse_length": 189,
        "protocol": 1,
        "sniffer_timeout": 30
    }


def sync_to_redis():
    """Sync current config to Redis for backend reads"""
    try:
        config = load_config()
        r = get_redis_client()
        r.set(REDIS_CONFIG_KEY, json.dumps(config.get('switches', [])))
        r.set(REDIS_SETTINGS_KEY, json.dumps(config.get('settings', {})))
        logging.info("Config synced to Redis")
        return True
    except Exception as e:
        logging.error(f"Failed to sync to Redis: {e}")
        return False


def get_switches():
    """Get all switches"""
    config = load_config()
    return config.get('switches', [])


def get_switch(switch_id):
    """Get a single switch by ID"""
    switches = get_switches()
    for switch in switches:
        if switch['id'] == switch_id:
            return switch
    return None


def get_next_id():
    """Get the next available switch ID"""
    switches = get_switches()
    if not switches:
        return 1
    return max(s['id'] for s in switches) + 1


def add_switch(name, on_code, off_code, switch_id=None):
    """Add a new switch"""
    config = load_config()
    switches = config.get('switches', [])
    
    # Auto-generate ID if not provided
    if switch_id is None:
        switch_id = get_next_id()
    
    # Check for duplicate ID
    if any(s['id'] == switch_id for s in switches):
        raise ValueError(f"Switch with ID {switch_id} already exists")
    
    new_switch = {
        "id": switch_id,
        "name": name,
        "on_code": on_code,
        "off_code": off_code
    }
    
    switches.append(new_switch)
    config['switches'] = switches
    save_config(config)
    sync_to_redis()
    
    logging.info(f"Added switch: {new_switch}")
    return new_switch


def update_switch(switch_id, name=None, on_code=None, off_code=None):
    """Update an existing switch"""
    config = load_config()
    switches = config.get('switches', [])
    
    for switch in switches:
        if switch['id'] == switch_id:
            if name is not None:
                switch['name'] = name
            if on_code is not None:
                switch['on_code'] = on_code
            if off_code is not None:
                switch['off_code'] = off_code
            
            config['switches'] = switches
            save_config(config)
            sync_to_redis()
            
            logging.info(f"Updated switch {switch_id}: {switch}")
            return switch
    
    raise ValueError(f"Switch with ID {switch_id} not found")


def delete_switch(switch_id):
    """Delete a switch"""
    config = load_config()
    switches = config.get('switches', [])
    
    original_len = len(switches)
    switches = [s for s in switches if s['id'] != switch_id]
    
    if len(switches) == original_len:
        raise ValueError(f"Switch with ID {switch_id} not found")
    
    config['switches'] = switches
    save_config(config)
    sync_to_redis()
    
    logging.info(f"Deleted switch {switch_id}")
    return True


def get_settings():
    """Get settings"""
    config = load_config()
    return config.get('settings', get_default_settings())


def update_settings(settings):
    """Update settings"""
    config = load_config()
    config['settings'] = {**config.get('settings', {}), **settings}
    save_config(config)
    sync_to_redis()
    return config['settings']


# Build outlets dict for controller compatibility
def get_outlets_dict():
    """Get outlets in the format controller.py expects"""
    switches = get_switches()
    return {
        s['id']: {"on": s['on_code'], "off": s['off_code']}
        for s in switches
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Test loading and syncing
    print("Loading config...")
    config = load_config()
    print(json.dumps(config, indent=2))
    
    print("\nSyncing to Redis...")
    sync_to_redis()
    print("Done!")
