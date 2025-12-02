#!/bin/bash

# CherryPi - Start All Services (Docker)
# This script launches all services using Docker Compose

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting CherryPi services with Docker..."

# Detect if running on Raspberry Pi
if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
    echo "Detected Raspberry Pi - using Pi configuration with GPIO access"
    docker compose -f docker-compose.yml -f docker-compose.pi.yml up -d --build
else
    echo "Not on Raspberry Pi - using development configuration"
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
fi

echo ""
echo "========================================"
echo "CherryPi services starting..."
echo "========================================"
echo ""

# Wait a moment for containers to start
sleep 3

# Show status
docker compose ps

echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Redis:     localhost:6379"
echo ""
echo "View logs: docker compose logs -f"
echo "Stop:      ./stop_all.sh"
