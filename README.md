# CherryPi

A full-stack application to control RF outlets using a Raspberry Pi, FastAPI, React, and Redis.

## Architecture

- **Frontend**: React (Port 3000)
- **Backend**: FastAPI (Port 8000)
- **Message Broker**: Redis (Port 6379)
- **Controller**: Python script (`redis_listener.py`) listening to Redis and sending RF codes via `rpi-rf`.

## Prerequisites

- Raspberry Pi (for RF control) or any machine (for development/simulation)
- Python 3.9+
- Node.js & npm
- Docker & Docker Compose (for Redis)

## System Setup (Raspberry Pi)

We have provided a convenience script to install Docker and Node.js.

1. **Run the setup script:**
   ```bash
   chmod +x setup_rpi.sh
   ./setup_rpi.sh
   ```
   *Note: You must log out and log back in (or restart) after running this script for Docker permissions to take effect.*

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/VirtualAdam/cherrypi.git
   cd cherrypi
   ```

2. **Set up Virtual Environment (Recommended):**
   ```bash
   python3 -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Raspberry Pi / Linux:
   source venv/bin/activate
   ```

3. **Start Redis:**
   ```bash
   docker compose up -d
   ```

4. **Backend Setup:**
   ```bash
   cd src/backend
   pip install -r requirements.txt
   # Run the server
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

5. **Frontend Setup:**
   ```bash
   cd src/frontend
   npm install
   npm start
   ```

6. **RF Controller (Raspberry Pi only):**
   ```bash
   cd src/RFController
   pip install -r requirements.txt
   python redis_listener.py
   ```

## Quick Start (All Services)

After completing the installation steps above, you can start all services with a single command:

```bash
chmod +x start_all.sh
./start_all.sh
```

To stop all services:
```bash
./stop_all.sh
```

## Docker (Recommended)

Run everything in Docker containers for a consistent experience on any platform.

### On Windows/Mac (Development)
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### On Raspberry Pi (Production)
```bash
docker compose -f docker-compose.yml -f docker-compose.pi.yml up -d
```

### Docker Commands
```bash
# View logs (all services)
docker compose logs -f

# View logs (single service)
docker compose logs -f backend

# Stop all services
docker compose down

# Rebuild after code changes
docker compose build
docker compose up -d
```

## Testing

Run unit tests with pytest:
```bash
pip install pytest httpx
pytest
```

## Troubleshooting

### Python 3.12+ Issues
If you are running Python 3.12 or newer (e.g., 3.13), you might encounter errors installing `RPi.GPIO` due to the removal of `distutils`.

**Solution:**
Install `setuptools` before installing requirements, or use `rpi-lgpio` as a drop-in replacement.

```bash
# Option 1: Install setuptools (restores distutils support)
pip install setuptools
pip install -r requirements.txt

# Option 2: Use rpi-lgpio (if Option 1 fails)
pip install rpi-lgpio
pip install rpi-rf --no-deps
pip install redis
```
cd ~/cherrypi && git pull && docker compose down && docker compose up -d --build