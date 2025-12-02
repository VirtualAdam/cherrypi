from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import redis
import os
import json
import logging
import uuid
import asyncio

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_CHANNEL = 'rf_commands'
CONFIG_COMMANDS_CHANNEL = 'config_commands'
CONFIG_RESPONSES_CHANNEL = 'config_responses'
SNIFFER_COMMANDS_CHANNEL = 'sniffer_commands'
SNIFFER_RESULTS_CHANNEL = 'sniffer_results'
CONFIG_SWITCHES_KEY = 'config:switches'

# Redis Connection
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
except Exception as e:
    logging.error(f"Failed to connect to Redis: {e}")
    r = None


# --- Pydantic Models ---

class OutletCommand(BaseModel):
    outlet_id: int
    state: str


class SwitchCreate(BaseModel):
    name: str
    on_code: int
    off_code: int
    id: Optional[int] = None


class SwitchUpdate(BaseModel):
    name: Optional[str] = None
    on_code: Optional[int] = None
    off_code: Optional[int] = None


class SnifferStart(BaseModel):
    capture_type: str = "on"  # 'on' or 'off'


# --- Helper Functions ---

async def wait_for_config_response(request_id: str, timeout: float = 5.0):
    """Wait for a response from config_listener via Redis pub/sub"""
    pubsub = r.pubsub()
    pubsub.subscribe(CONFIG_RESPONSES_CHANNEL)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        while True:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('request_id') == request_id:
                    return data
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise HTTPException(status_code=504, detail="Config service timeout")
            
            await asyncio.sleep(0.05)
    finally:
        pubsub.unsubscribe(CONFIG_RESPONSES_CHANNEL)
        pubsub.close()


async def send_config_command(action: str, data: dict = None, timeout: float = 5.0):
    """Send a command to config_listener and wait for response"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    request_id = str(uuid.uuid4())
    
    payload = json.dumps({
        "action": action,
        "request_id": request_id,
        "data": data or {}
    })
    
    r.publish(CONFIG_COMMANDS_CHANNEL, payload)
    response = await wait_for_config_response(request_id, timeout)
    
    if not response.get('success'):
        raise HTTPException(status_code=400, detail=response.get('error', 'Unknown error'))
    
    return response.get('data')

@app.post("/api/outlet")
async def control_outlet(command: OutletCommand):
    if command.state.lower() not in ['on', 'off']:
        raise HTTPException(status_code=400, detail="State must be 'on' or 'off'")

    if r is None:
         raise HTTPException(status_code=503, detail="Redis connection unavailable")

    # Validate outlet exists by checking config
    switches_json = r.get(CONFIG_SWITCHES_KEY)
    if switches_json:
        switches = json.loads(switches_json)
        valid_ids = [s['id'] for s in switches]
        if command.outlet_id not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Invalid outlet ID: {command.outlet_id}")
    
    payload = json.dumps({
        "outlet": command.outlet_id,
        "state": command.state.lower()
    })
    
    try:
        r.publish(REDIS_CHANNEL, payload)
        return {"status": "success", "message": f"Sent {command.state} command to outlet {command.outlet_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")


# --- Switch Management Endpoints ---

@app.get("/api/switches")
async def get_switches():
    """Get all switches from config"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    # Try to get from Redis cache first (faster)
    switches_json = r.get(CONFIG_SWITCHES_KEY)
    if switches_json:
        return json.loads(switches_json)
    
    # If no data in Redis, try to query config_listener
    # If that fails too, return empty list (rf-controller might not be running)
    try:
        return await send_config_command("get_switches", timeout=2.0)
    except HTTPException:
        # Config service not available, return empty list
        return []


@app.get("/api/switches/{switch_id}")
async def get_switch(switch_id: int):
    """Get a single switch by ID"""
    return await send_config_command("get_switch", {"id": switch_id})


@app.post("/api/switches")
async def create_switch(switch: SwitchCreate):
    """Create a new switch"""
    data = {
        "name": switch.name,
        "on_code": switch.on_code,
        "off_code": switch.off_code
    }
    if switch.id is not None:
        data["id"] = switch.id
    
    return await send_config_command("add_switch", data)


@app.put("/api/switches/{switch_id}")
async def update_switch(switch_id: int, switch: SwitchUpdate):
    """Update an existing switch"""
    data = {"id": switch_id}
    if switch.name is not None:
        data["name"] = switch.name
    if switch.on_code is not None:
        data["on_code"] = switch.on_code
    if switch.off_code is not None:
        data["off_code"] = switch.off_code
    
    return await send_config_command("update_switch", data)


@app.delete("/api/switches/{switch_id}")
async def delete_switch(switch_id: int):
    """Delete a switch"""
    return await send_config_command("delete_switch", {"id": switch_id})


@app.get("/api/switches/next-id")
async def get_next_switch_id():
    """Get the next available switch ID"""
    return await send_config_command("get_next_id")


# --- Sniffer Endpoints ---

# Store for tracking sniffer results
sniffer_results = {}


async def wait_for_sniffer_result(request_id: str, timeout: float = 35.0):
    """Wait for sniffer result via Redis pub/sub"""
    pubsub = r.pubsub()
    pubsub.subscribe(SNIFFER_RESULTS_CHANNEL)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        while True:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('request_id') == request_id:
                    return data
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                return {"event": "timeout", "error": "Sniffer timeout"}
            
            await asyncio.sleep(0.05)
    finally:
        pubsub.unsubscribe(SNIFFER_RESULTS_CHANNEL)
        pubsub.close()


@app.post("/api/sniffer/start")
async def start_sniffer(params: SnifferStart):
    """Start the RF sniffer to capture a code"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    if params.capture_type not in ['on', 'off']:
        raise HTTPException(status_code=400, detail="capture_type must be 'on' or 'off'")
    
    request_id = str(uuid.uuid4())
    
    payload = json.dumps({
        "action": "start",
        "request_id": request_id,
        "capture_type": params.capture_type
    })
    
    r.publish(SNIFFER_COMMANDS_CHANNEL, payload)
    
    # Wait for result (blocking call - will wait until code captured or timeout)
    result = await wait_for_sniffer_result(request_id)
    
    return result


@app.post("/api/sniffer/stop")
async def stop_sniffer():
    """Stop the RF sniffer"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    request_id = str(uuid.uuid4())
    
    payload = json.dumps({
        "action": "stop",
        "request_id": request_id
    })
    
    r.publish(SNIFFER_COMMANDS_CHANNEL, payload)
    
    return {"status": "stop command sent"}


@app.get("/api/sniffer/status")
async def get_sniffer_status():
    """Get current sniffer status"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    status_json = r.get('sniffer:status')
    if status_json:
        return json.loads(status_json)
    
    return {"active": False}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
