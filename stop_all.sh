#!/bin/bash

# CherryPi - Stop All Services

echo "Stopping CherryPi services..."

# Kill uvicorn (backend)
pkill -f "uvicorn main:app" 2>/dev/null && echo "Backend stopped." || echo "Backend not running."

# Kill npm/node (frontend)
pkill -f "react-scripts start" 2>/dev/null && echo "Frontend stopped." || echo "Frontend not running."
pkill -f "node.*frontend" 2>/dev/null

# Kill RF controller
pkill -f "redis_listener.py" 2>/dev/null && echo "RF Controller stopped." || echo "RF Controller not running."

echo "All services stopped."
