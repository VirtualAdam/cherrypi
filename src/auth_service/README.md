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

**Prerequisites:**
- Keyboard and monitor connected to your Raspberry Pi
- Docker containers running (`docker compose up -d`)

**Steps:**

1. Connect keyboard and monitor to Raspberry Pi
2. Login to the Pi locally (not via SSH)
3. Navigate to the CherryPi project directory:

```bash
cd ~/CherryPi   # or wherever you cloned the project
```

4. Generate your encryption keys (do this ONCE and save them!):

```bash
# Generate a secure random key - SAVE THIS OUTPUT!
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Important:** Copy the output! This will be your `AUTH_DB_KEY`. You'll need to:
- Use this same key every time you run these scripts
- Add it to your `.env` file for Docker
- If you lose this key, you cannot recover your user database!

5. Set environment variables and run:

```bash
# Set the encryption key (paste the key you generated above)
export AUTH_DB_KEY='paste-your-64-character-key-here'

# Set the data directory (this is where users.enc will be stored)
# Use the Docker volume path so the auth service container can read it:
export AUTH_DATA_DIR='/var/lib/docker/volumes/cherrypi_auth_data/_data'

# Or if you prefer a simpler local path for testing:
# export AUTH_DATA_DIR="$HOME/CherryPi/data"
# mkdir -p $AUTH_DATA_DIR

# Run the provisioning CLI (from the project root directory)
sudo -E python3 src/auth_service/secure_user_add.py
```

Note: `sudo -E` preserves your environment variables when running as root.

6. **Save your key!** Add it to your `.env` file:

```bash
# Create .env from the example
cp .env.example .env

# Edit and add your key
nano .env
# Set: AUTH_DB_KEY=paste-your-64-character-key-here
# Set: JWT_SECRET_KEY=generate-another-key-for-this
```

7. Restart Docker to pick up the new keys:

```bash
docker compose down
docker compose up -d
```

### Generate Magic QR Code

1. From physical console (keyboard + monitor on Pi):

```bash
cd ~/CherryPi  # Navigate to project directory

# Use the SAME AUTH_DB_KEY you created above
export AUTH_DB_KEY='paste-your-64-character-key-here'
export REDIS_HOST='localhost'  # Or Redis container IP
export CHERRYPI_URL='http://cherrypi.local:3000'  # Your Pi's URL

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
