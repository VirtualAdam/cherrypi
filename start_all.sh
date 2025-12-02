#!/bin/bash

# CherryPi - Start All Services
# This script launches the backend, frontend, and RF controller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting CherryPi services..."

# Start Redis if not running
if ! docker ps | grep -q redis; then
    echo "Starting Redis..."
    docker compose up -d
    sleep 2
fi

# Create logs directory
mkdir -p logs

# Start Backend (FastAPI)
echo "Starting Backend on port 8000..."
cd src/backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Start Frontend (React)
echo "Starting Frontend on port 3000..."
cd src/frontend
npm start > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

# Start RF Controller
echo "Starting RF Controller..."
cd src/RFController
python redis_listener.py > ../../logs/rf_controller.log 2>&1 &
RF_PID=$!
cd ../..

echo ""
echo "========================================"
echo "CherryPi is running!"
echo "========================================"
echo "Frontend:  http://$(hostname -I | awk '{print $1}'):3000"
echo "Backend:   http://$(hostname -I | awk '{print $1}'):8000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services"

# Handle shutdown
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill $RF_PID 2>/dev/null
    echo "All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for any process to exit
wait
