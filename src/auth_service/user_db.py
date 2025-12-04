"""
CherryPi Auth Service - Encrypted User Database

Handles user storage with Fernet encryption at rest.
"""

import json
import logging
import os
import uuid
from typing import Optional, Dict, List

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger('auth_service.user_db')


def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """Derive a Fernet-compatible key from a password."""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


class UserDatabase:
    """
    Encrypted user database manager.
    
    The database is stored as an encrypted JSON file.
    Structure:
    {
        "users": {
            "user_id": {
                "id": "uuid",
                "username": "string",
                "password_hash": "bcrypt_hash",
                "role": "admin|user|guest",
                "created_at": "iso_timestamp",
                "created_by": "username"
            }
        },
        "salt": "base64_encoded_salt"
    }
    """
    
    def __init__(self, db_path: str, encryption_key: str):
        self.db_path = db_path
        self.encryption_key = encryption_key
        self._data = None
        self._fernet = None
        self._salt = None
        
        self._load_or_create()
    
    def _load_or_create(self):
        """Load existing database or create a new one."""
        if os.path.exists(self.db_path):
            self._load()
        else:
            self._create_new()
    
    def _create_new(self):
        """Create a new empty database."""
        # Generate salt and derive key
        key, salt = derive_key_from_password(self.encryption_key)
        self._salt = salt
        self._fernet = Fernet(key)
        
        self._data = {
            'users': {},
            'salt': base64.b64encode(salt).decode('utf-8')
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._save()
        logger.info(f"Created new user database at {self.db_path}")
    
    def _load(self):
        """Load and decrypt the database."""
        try:
            with open(self.db_path, 'rb') as f:
                encrypted_data = f.read()
            
            # First, we need to extract the salt from the file header
            # Format: salt (16 bytes) + encrypted data
            if len(encrypted_data) < 16:
                raise ValueError("Database file is corrupted")
            
            self._salt = encrypted_data[:16]
            encrypted_content = encrypted_data[16:]
            
            # Derive key from password and salt
            key, _ = derive_key_from_password(self.encryption_key, self._salt)
            self._fernet = Fernet(key)
            
            # Decrypt
            decrypted = self._fernet.decrypt(encrypted_content)
            self._data = json.loads(decrypted.decode('utf-8'))
            
            logger.info(f"Loaded user database with {len(self._data.get('users', {}))} users")
            
        except InvalidToken:
            logger.error("Failed to decrypt database - invalid encryption key")
            raise ValueError("Invalid encryption key")
        except Exception as e:
            logger.error(f"Failed to load database: {e}")
            raise
    
    def _save(self):
        """Encrypt and save the database."""
        try:
            # Serialize data
            json_data = json.dumps(self._data, indent=2)
            
            # Encrypt
            encrypted = self._fernet.encrypt(json_data.encode('utf-8'))
            
            # Write salt + encrypted data
            with open(self.db_path, 'wb') as f:
                f.write(self._salt)
                f.write(encrypted)
            
            logger.debug("Database saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
            raise
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    def add_user(self, username: str, password: str, role: str, created_by: str = 'system') -> Dict:
        """
        Add a new user to the database.
        
        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            role: User role (admin, user, guest)
            created_by: Username of the creator
            
        Returns:
            The created user dict (without password hash)
        """
        # Validate role
        if role not in ['admin', 'user', 'guest']:
            raise ValueError(f"Invalid role: {role}")
        
        # Check for duplicate username
        for user in self._data['users'].values():
            if user['username'].lower() == username.lower():
                raise ValueError(f"Username '{username}' already exists")
        
        # Create user
        user_id = str(uuid.uuid4())
        from datetime import datetime
        
        user = {
            'id': user_id,
            'username': username,
            'password_hash': self._hash_password(password),
            'role': role,
            'created_at': datetime.utcnow().isoformat(),
            'created_by': created_by
        }
        
        self._data['users'][user_id] = user
        self._save()
        
        logger.info(f"User '{username}' created with role '{role}'")
        
        # Return user without password hash
        return {k: v for k, v in user.items() if k != 'password_hash'}
    
    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify user credentials.
        
        Returns:
            User dict (without password hash) if valid, None otherwise
        """
        for user in self._data['users'].values():
            if user['username'].lower() == username.lower():
                if self._verify_password(password, user['password_hash']):
                    return {k: v for k, v in user.items() if k != 'password_hash'}
                break
        return None
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        user = self._data['users'].get(user_id)
        if user:
            return {k: v for k, v in user.items() if k != 'password_hash'}
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get a user by username."""
        for user in self._data['users'].values():
            if user['username'].lower() == username.lower():
                return {k: v for k, v in user.items() if k != 'password_hash'}
        return None
    
    def list_users(self) -> List[Dict]:
        """List all users (without password hashes)."""
        return [
            {k: v for k, v in user.items() if k != 'password_hash'}
            for user in self._data['users'].values()
        ]
    
    def update_user(self, user_id: str, **kwargs) -> Optional[Dict]:
        """
        Update a user.
        
        Allowed fields: username, password, role
        """
        if user_id not in self._data['users']:
            return None
        
        user = self._data['users'][user_id]
        
        if 'username' in kwargs:
            # Check for duplicate
            new_username = kwargs['username']
            for u in self._data['users'].values():
                if u['id'] != user_id and u['username'].lower() == new_username.lower():
                    raise ValueError(f"Username '{new_username}' already exists")
            user['username'] = new_username
        
        if 'password' in kwargs:
            user['password_hash'] = self._hash_password(kwargs['password'])
        
        if 'role' in kwargs:
            if kwargs['role'] not in ['admin', 'user', 'guest']:
                raise ValueError(f"Invalid role: {kwargs['role']}")
            user['role'] = kwargs['role']
        
        self._save()
        
        return {k: v for k, v in user.items() if k != 'password_hash'}
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        if user_id in self._data['users']:
            username = self._data['users'][user_id]['username']
            del self._data['users'][user_id]
            self._save()
            logger.info(f"User '{username}' deleted")
            return True
        return False
    
    def user_count(self) -> int:
        """Get the number of users."""
        return len(self._data['users'])
    
    def has_admin(self) -> bool:
        """Check if at least one admin user exists."""
        return any(
            user['role'] == 'admin'
            for user in self._data['users'].values()
        )
