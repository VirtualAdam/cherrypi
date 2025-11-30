from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import os
import json
import logging

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

# Redis Connection
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
except Exception as e:
    logging.error(f"Failed to connect to Redis: {e}")
    r = None

class OutletCommand(BaseModel):
    outlet_id: int
    state: str

@app.post("/api/outlet")
async def control_outlet(command: OutletCommand):
    if command.state.lower() not in ['on', 'off']:
        raise HTTPException(status_code=400, detail="State must be 'on' or 'off'")
    
    if not (1 <= command.outlet_id <= 5):
        raise HTTPException(status_code=400, detail="Outlet ID must be between 1 and 5")

    if r is None:
         raise HTTPException(status_code=503, detail="Redis connection unavailable")

    payload = json.dumps({
        "outlet": command.outlet_id,
        "state": command.state.lower()
    })
    
    try:
        r.publish(REDIS_CHANNEL, payload)
        return {"status": "success", "message": f"Sent {command.state} command to outlet {command.outlet_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
