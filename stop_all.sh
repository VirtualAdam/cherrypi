#!/bin/bash

# CherryPi - Stop All Services (Docker)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping CherryPi services..."

docker compose down

echo ""
echo "All services stopped."
