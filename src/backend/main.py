from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
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

# Auth channels
AUTH_REQUESTS_CHANNEL = 'auth:requests'
AUTH_RESPONSES_CHANNEL = 'auth:responses'

# Auth configuration - set to 'false' or '0' to disable authentication
AUTH_ENABLED = os.getenv('AUTH_ENABLED', 'true').lower() not in ('false', '0', 'no', 'disabled')

# Security
security = HTTPBearer(auto_error=False)

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


# --- Auth Models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class MagicCodeRequest(BaseModel):
    code: str
    role: Optional[str] = "guest"


class AuthUser(BaseModel):
    """Represents an authenticated user from token verification"""
    user_id: str
    username: str
    role: str
    scope: str


# --- Auth Helper Functions ---

async def wait_for_auth_response(request_id: str, timeout: float = 5.0):
    """Wait for a response from auth service via Redis pub/sub"""
    pubsub = r.pubsub()
    pubsub.subscribe(AUTH_RESPONSES_CHANNEL)
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        while True:
            message = pubsub.get_message(timeout=0.1)
            if message and message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get('request_id') == request_id:
                    return data
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise HTTPException(status_code=504, detail="Auth service timeout")
            
            await asyncio.sleep(0.05)
    finally:
        pubsub.unsubscribe(AUTH_RESPONSES_CHANNEL)
        pubsub.close()


async def send_auth_command(cmd: str, data: dict = None, timeout: float = 5.0):
    """Send a command to auth service and wait for response"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    request_id = str(uuid.uuid4())
    
    payload = {
        "cmd": cmd,
        "request_id": request_id,
        **(data or {})
    }
    
    r.publish(AUTH_REQUESTS_CHANNEL, json.dumps(payload))
    response = await wait_for_auth_response(request_id, timeout)
    
    return response


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> AuthUser:
    """Dependency to verify JWT token and return user info"""
    # If auth is disabled, return a default admin user
    if not AUTH_ENABLED:
        return AuthUser(
            user_id='anonymous',
            username='anonymous',
            role='admin',
            scope='read:all write:all admin:users'
        )
    
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    
    try:
        response = await send_auth_command("verify", {"token": token})
    except HTTPException as e:
        # If auth service is unavailable and we want graceful degradation
        if e.status_code == 504:  # Timeout
            logging.warning("Auth service unavailable, denying request")
        raise
    
    if not response.get('valid'):
        raise HTTPException(
            status_code=401, 
            detail=response.get('error', 'Invalid token')
        )
    
    return AuthUser(
        user_id=response.get('user_id', ''),
        username=response.get('username', ''),
        role=response.get('role', 'guest'),
        scope=response.get('scope', '')
    )


async def verify_token_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[AuthUser]:
    """Optional token verification - returns None if no token provided"""
    if credentials is None:
        return None
    
    try:
        return await verify_token(credentials)
    except HTTPException:
        return None


def require_scope(required_scope: str):
    """Dependency factory to check for required scope"""
    async def check_scope(user: AuthUser = Depends(verify_token)) -> AuthUser:
        user_scopes = user.scope.split()
        
        # Check if user has the required scope or wildcard permissions
        has_permission = (
            required_scope in user_scopes or
            'write:all' in user_scopes or
            (required_scope.startswith('read:') and 'read:all' in user_scopes)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403, 
                detail=f"Insufficient permissions. Required: {required_scope}"
            )
        
        return user
    
    return check_scope


def require_admin():
    """Dependency to require admin role"""
    async def check_admin(user: AuthUser = Depends(verify_token)) -> AuthUser:
        if user.role != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")
        return user
    
    return check_admin


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
                    event = data.get('event')
                    # Only return on terminal events (captured, error, no_code, timeout)
                    # Skip 'started' event - that's just a progress notification
                    if event in ['captured', 'error', 'no_code', 'timeout', 'stopped']:
                        logging.info(f"Sniffer result: {event} for request {request_id}")
                        return data
                    else:
                        logging.info(f"Sniffer progress: {event} for request {request_id}")
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                return {"event": "timeout", "error": "Sniffer timeout - no response from RF controller"}
            
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


@app.get("/foundation")
async def foundation_redirect(request: Request):
    """
    Redirect to the Family Foundation static site on port 8080.
    This allows accessing the foundation site via /foundation without logging in.
    """
    # Get the original host from X-Forwarded-Host (set by proxy) or fall back to Host header
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost")
    # Remove port if present
    host = host.split(":")[0]
    return RedirectResponse(url=f"http://{host}:8080", status_code=302)


# --- Auth Endpoints ---

@app.get("/api/auth/status")
async def auth_status():
    """
    Check if authentication is enabled.
    Frontend can use this to skip login page if auth is disabled.
    """
    return {
        "auth_enabled": AUTH_ENABLED
    }


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    
    Returns:
        - token: JWT token for authenticated requests
        - role: User's role (admin, user, guest)
        - username: User's username
    """
    response = await send_auth_command("login", {
        "username": request.username,
        "password": request.password
    })
    
    if not response.get('success'):
        raise HTTPException(
            status_code=401, 
            detail=response.get('error', 'Authentication failed')
        )
    
    return {
        "token": response.get('token'),
        "role": response.get('role'),
        "username": response.get('username')
    }


@app.post("/api/auth/verify")
async def verify_auth(user: AuthUser = Depends(verify_token)):
    """
    Verify the current token and return user info.
    Used by frontend to check if token is still valid.
    """
    return {
        "valid": True,
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "scope": user.scope
    }


@app.get("/api/auth/me")
async def get_current_user(user: AuthUser = Depends(verify_token)):
    """Get current authenticated user's information."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "scope": user.scope
    }


@app.post("/api/auth/magic/verify")
async def verify_magic_code(request: MagicCodeRequest):
    """
    Verify a magic code and return a long-lived token.
    Magic codes are generated by admins via physical console.
    
    Args:
        code: The magic code from QR scan
        role: Desired role (user or guest, not admin)
    """
    response = await send_auth_command("magic_verify", {
        "code": request.code,
        "role": request.role
    })
    
    if not response.get('success'):
        raise HTTPException(
            status_code=401,
            detail=response.get('error', 'Invalid magic code')
        )
    
    return {
        "token": response.get('token'),
        "role": response.get('role')
    }


# --- Protected Endpoints (with auth) ---
# Note: For backward compatibility, endpoints below are protected versions
# The existing endpoints remain unchanged for now

@app.post("/api/secure/outlet")
async def control_outlet_secure(
    command: OutletCommand,
    user: AuthUser = Depends(require_scope("write:switches"))
):
    """Control an outlet (requires write:switches scope)"""
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
        logging.info(f"User '{user.username}' controlled outlet {command.outlet_id} -> {command.state}")
        return {"status": "success", "message": f"Sent {command.state} command to outlet {command.outlet_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis Error: {str(e)}")


@app.get("/api/secure/switches")
async def get_switches_secure(user: AuthUser = Depends(require_scope("read:switches"))):
    """Get all switches (requires read:switches scope)"""
    if r is None:
        raise HTTPException(status_code=503, detail="Redis connection unavailable")
    
    switches_json = r.get(CONFIG_SWITCHES_KEY)
    if switches_json:
        return json.loads(switches_json)
    
    try:
        return await send_config_command("get_switches", timeout=2.0)
    except HTTPException:
        return []


@app.post("/api/secure/switches")
async def create_switch_secure(
    switch: SwitchCreate,
    user: AuthUser = Depends(require_scope("write:switches"))
):
    """Create a new switch (requires write:switches scope)"""
    data = {
        "name": switch.name,
        "on_code": switch.on_code,
        "off_code": switch.off_code
    }
    if switch.id is not None:
        data["id"] = switch.id
    
    logging.info(f"User '{user.username}' creating switch: {switch.name}")
    return await send_config_command("add_switch", data)


@app.put("/api/secure/switches/{switch_id}")
async def update_switch_secure(
    switch_id: int,
    switch: SwitchUpdate,
    user: AuthUser = Depends(require_scope("write:switches"))
):
    """Update an existing switch (requires write:switches scope)"""
    data = {"id": switch_id}
    if switch.name is not None:
        data["name"] = switch.name
    if switch.on_code is not None:
        data["on_code"] = switch.on_code
    if switch.off_code is not None:
        data["off_code"] = switch.off_code
    
    logging.info(f"User '{user.username}' updating switch {switch_id}")
    return await send_config_command("update_switch", data)


@app.delete("/api/secure/switches/{switch_id}")
async def delete_switch_secure(
    switch_id: int,
    user: AuthUser = Depends(require_scope("write:switches"))
):
    """Delete a switch (requires write:switches scope)"""
    logging.info(f"User '{user.username}' deleting switch {switch_id}")
    return await send_config_command("delete_switch", {"id": switch_id})

