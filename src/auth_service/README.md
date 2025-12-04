# CherryPi Auth Service

Secure, decoupled authentication service for CherryPi using Redis-based RPC.

## Architecture

The Auth Service is the **Policy Decision Point (PDP)** and **Identity Provider** for CherryPi:

- **Backend** asks Auth Service "Is this token valid?"
- **Auth Service** validates credentials, mints JWTs, and manages magic codes
- Communication happens via Redis pub/sub channels

## Features

- **Scoped JWTs** with Role-Based Access Control (RBAC)
- **Magic QR Code Login** for frictionless mobile onboarding
- **Encryption at Rest** - User database is encrypted using Fernet
- **Physical-Only Provisioning** - Admin users can only be created from physical console

## Roles & Permissions

| Role | Scope | Can Do |
|------|-------|--------|
| `admin` | `read:all write:all admin:users` | Everything + create users + generate magic codes |
| `user` | `read:switches write:switches` | View and control switches, edit switch config |
| `guest` | `read:switches` | View and control switches only |

## Files

- `auth_service.py` - Main service (runs in Docker)
- `user_db.py` - Encrypted user database manager
- `magic_code.py` - Magic code generation and verification
- `secure_user_add.py` - Physical-console-only user provisioning CLI
- `generate_magic_qr.py` - Physical-console-only QR code generator

## Physical Console Scripts

These scripts **only work from a physical console** (keyboard + monitor attached to the Pi). They will refuse to run over SSH.

### Create First Admin User

1. Connect keyboard and monitor to Raspberry Pi
2. Login to the Pi locally
3. Run:

```bash
# Set the encryption key (same as AUTH_DB_KEY in docker-compose)
export AUTH_DB_KEY='your-encryption-key'
export AUTH_DATA_DIR='/path/to/data'  # Or use Docker volume path

# Run the provisioning CLI
sudo python3 src/auth_service/secure_user_add.py
```

### Generate Magic QR Code

1. From physical console:

```bash
export AUTH_DB_KEY='your-encryption-key'
export REDIS_HOST='localhost'  # Or Redis container IP
export CHERRYPI_URL='http://cherrypi.local:3000'

python3 src/auth_service/generate_magic_qr.py
```

2. The script will:
   - Authenticate you as admin
   - Generate a magic code
   - Save QR code as HTML and PNG to `/tmp/cherrypi/`
   - Optionally open in browser

3. Scan the QR code with a mobile device to login

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_HOST` | Redis hostname | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `JWT_SECRET_KEY` | Secret for signing JWTs | (required) |
| `AUTH_DB_KEY` | Key for encrypting user database | (required) |
| `AUTH_DATA_DIR` | Directory for user database | `/data` |
| `CHERRYPI_URL` | Frontend URL for magic codes | `http://cherrypi.local:3000` |

## Redis Channels

| Channel | Direction | Purpose |
|---------|-----------|---------|
| `auth:requests` | Backend → Auth | Login, verify, magic code requests |
| `auth:responses` | Auth → Backend | Responses with tokens/results |

## Token Expiration

- **Web login tokens**: 24 hours
- **Magic QR tokens**: 1 year (for devices)

## Security Notes

1. **Never commit** `.env` files with real keys
2. **Generate strong keys** using `secrets.token_hex(32)`
3. **Physical provisioning** prevents remote attackers from creating admin accounts
4. **Encrypted database** protects credentials even if storage is compromised
