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

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/VirtualAdam/cherrypi.git
   cd cherrypi
   ```

2. **Start Redis:**
   ```bash
   docker-compose up -d
   ```

3. **Backend Setup:**
   ```bash
   cd src/backend
   pip install -r requirements.txt
   # Run the server
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

4. **Frontend Setup:**
   ```bash
   cd src/frontend
   npm install
   npm start
   ```

5. **RF Controller (Raspberry Pi only):**
   ```bash
   cd src/RFController
   pip install -r requirements.txt
   python redis_listener.py
   ```

## Testing

Run unit tests with pytest:
```bash
pip install pytest httpx
pytest
```
