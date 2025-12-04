"""
CherryPi Auth Service - Main Entry Point

This service handles all authentication and authorization via Redis pub/sub.
It is the Policy Decision Point (PDP) and Identity Provider.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta

import jwt
import redis

from user_db import UserDatabase
from magic_code import MagicCodeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auth_service')

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-me-in-production')
AUTH_DB_KEY = os.getenv('AUTH_DB_KEY', 'change-me-in-production-db-key')
DATA_DIR = os.getenv('AUTH_DATA_DIR', '/data')

# Token expiration times
WEB_TOKEN_EXPIRY_HOURS = 24  # 1 day for web login
MAGIC_TOKEN_EXPIRY_DAYS = 365  # 1 year for magic QR login

# Redis channels
AUTH_REQUESTS_CHANNEL = 'auth:requests'
AUTH_RESPONSES_CHANNEL = 'auth:responses'

# Role definitions with scopes
ROLE_SCOPES = {
    'admin': 'read:all write:all admin:users',
    'user': 'read:switches write:switches',
    'guest': 'read:switches'
}


class AuthService:
    """Main authentication service that listens for requests via Redis."""
    
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.user_db = None
        self.magic_code_manager = None
        self.running = False
        
    def connect_redis(self):
        """Establish connection to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def initialize(self):
        """Initialize all components."""
        # Connect to Redis
        if not self.connect_redis():
            return False
        
        # Initialize user database
        db_path = os.path.join(DATA_DIR, 'users.enc')
        self.user_db = UserDatabase(db_path, AUTH_DB_KEY)
        logger.info(f"User database initialized at {db_path}")
        
        # Initialize magic code manager
        self.magic_code_manager = MagicCodeManager(self.redis_client)
        logger.info("Magic code manager initialized")
        
        return True
    
    def generate_token(self, user_id: str, username: str, role: str, long_lived: bool = False) -> str:
        """Generate a JWT token for a user."""
        if long_lived:
            expiry = datetime.utcnow() + timedelta(days=MAGIC_TOKEN_EXPIRY_DAYS)
        else:
            expiry = datetime.utcnow() + timedelta(hours=WEB_TOKEN_EXPIRY_HOURS)
        
        scope = ROLE_SCOPES.get(role, ROLE_SCOPES['guest'])
        
        payload = {
            'sub': user_id,
            'username': username,
            'role': role,
            'scope': scope,
            'exp': expiry,
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    
    def verify_token(self, token: str) -> dict:
        """Verify a JWT token and return its payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            return {
                'valid': True,
                'user_id': payload.get('sub'),
                'username': payload.get('username'),
                'role': payload.get('role'),
                'scope': payload.get('scope', '')
            }
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': f'Invalid token: {str(e)}'}
    
    def handle_login(self, data: dict) -> dict:
        """Handle a login request."""
        username = data.get('username', '').strip()
        password = data.get('password', '')
        request_id = data.get('request_id')
        
        if not username or not password:
            return {
                'request_id': request_id,
                'success': False,
                'error': 'Username and password required'
            }
        
        # Verify credentials
        user = self.user_db.verify_user(username, password)
        
        if user:
            token = self.generate_token(
                user_id=user['id'],
                username=user['username'],
                role=user['role']
            )
            logger.info(f"User '{username}' logged in successfully")
            return {
                'request_id': request_id,
                'success': True,
                'token': token,
                'role': user['role'],
                'username': user['username']
            }
        else:
            logger.warning(f"Failed login attempt for user '{username}'")
            return {
                'request_id': request_id,
                'success': False,
                'error': 'Invalid credentials'
            }
    
    def handle_verify(self, data: dict) -> dict:
        """Handle a token verification request."""
        token = data.get('token', '')
        required_scope = data.get('required_scope', '')
        request_id = data.get('request_id')
        
        result = self.verify_token(token)
        result['request_id'] = request_id
        
        # Check scope if required
        if result.get('valid') and required_scope:
            user_scopes = result.get('scope', '').split()
            # Check if user has the required scope or 'write:all'/'read:all'
            has_scope = (
                required_scope in user_scopes or
                'write:all' in user_scopes or
                (required_scope.startswith('read:') and 'read:all' in user_scopes)
            )
            if not has_scope:
                result['valid'] = False
                result['error'] = 'Insufficient permissions'
        
        return result
    
    def handle_magic_code_generate(self, data: dict) -> dict:
        """Generate a magic code for QR login."""
        token = data.get('token', '')
        request_id = data.get('request_id')
        
        # Verify the requesting user is an admin
        verify_result = self.verify_token(token)
        if not verify_result.get('valid'):
            return {
                'request_id': request_id,
                'success': False,
                'error': 'Invalid token'
            }
        
        if verify_result.get('role') != 'admin':
            return {
                'request_id': request_id,
                'success': False,
                'error': 'Admin access required'
            }
        
        # Generate magic code
        code = self.magic_code_manager.generate_code(
            created_by=verify_result.get('username')
        )
        
        logger.info(f"Magic code generated by admin '{verify_result.get('username')}'")
        
        return {
            'request_id': request_id,
            'success': True,
            'code': code,
            'expires_in': 300  # 5 minutes
        }
    
    def handle_magic_code_verify(self, data: dict) -> dict:
        """Verify and consume a magic code, returning a long-lived token."""
        code = data.get('code', '')
        request_id = data.get('request_id')
        target_role = data.get('role', 'guest')  # Default to guest for magic login
        
        # Validate target role (magic code can only create user or guest, not admin)
        if target_role not in ['user', 'guest']:
            target_role = 'guest'
        
        # Verify and burn the magic code
        code_data = self.magic_code_manager.verify_and_burn(code)
        
        if not code_data:
            return {
                'request_id': request_id,
                'success': False,
                'error': 'Invalid or expired magic code'
            }
        
        # Generate a long-lived token for the device
        # Use a device identifier as the user
        device_id = f"magic_device_{code}"
        token = self.generate_token(
            user_id=device_id,
            username=f"device_{code[:8]}",
            role=target_role,
            long_lived=True
        )
        
        logger.info(f"Magic code redeemed, device token issued with role '{target_role}'")
        
        return {
            'request_id': request_id,
            'success': True,
            'token': token,
            'role': target_role
        }
    
    def handle_request(self, message: dict):
        """Route a request to the appropriate handler."""
        cmd = message.get('cmd', '')
        
        handlers = {
            'login': self.handle_login,
            'verify': self.handle_verify,
            'magic_generate': self.handle_magic_code_generate,
            'magic_verify': self.handle_magic_code_verify
        }
        
        handler = handlers.get(cmd)
        if handler:
            response = handler(message)
        else:
            response = {
                'request_id': message.get('request_id'),
                'success': False,
                'error': f'Unknown command: {cmd}'
            }
        
        # Publish response
        self.redis_client.publish(AUTH_RESPONSES_CHANNEL, json.dumps(response))
    
    def run(self):
        """Main run loop - listen for auth requests."""
        if not self.initialize():
            logger.error("Failed to initialize auth service")
            sys.exit(1)
        
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(AUTH_REQUESTS_CHANNEL)
        self.running = True
        
        logger.info(f"Auth service listening on channel '{AUTH_REQUESTS_CHANNEL}'")
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        self.handle_request(data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in message: {message['data']}")
            except redis.ConnectionError:
                logger.error("Lost connection to Redis, attempting to reconnect...")
                if self.connect_redis():
                    self.pubsub = self.redis_client.pubsub()
                    self.pubsub.subscribe(AUTH_REQUESTS_CHANNEL)
                else:
                    asyncio.sleep(5)
        
        self.cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("Auth service stopped")


if __name__ == '__main__':
    service = AuthService()
    service.run()
