#!/bin/bash

# CherryPi - Raspberry Pi System Setup Script
# This script installs Docker and Node.js required for the project.

# Note: Removed 'set -e' to prevent abrupt exits on minor errors
# which can leave the system in a broken state.

echo "Starting CherryPi System Setup..."

# Ensure we're running on a Raspberry Pi / Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Error: This script is intended for Raspberry Pi / Linux only."
    exit 1
fi

# Ensure we have the current username
if [ -z "$USER" ]; then
    USER=$(whoami)
fi
echo "Running as user: $USER"

# --- Docker Installation ---
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    if sudo sh get-docker.sh; then
        rm get-docker.sh
        echo "Adding current user ($USER) to the docker group..."
        sudo usermod -aG docker "$USER"
        echo "Docker installed successfully."
    else
        echo "ERROR: Docker installation failed!"
        rm -f get-docker.sh
        exit 1
    fi
else
    echo "Docker is already installed."
fi

# --- Node.js Installation ---
if ! command -v node &> /dev/null; then
    echo "Node.js not found. Installing Node.js (v18)..."
    if curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -; then
        sudo apt-get install -y nodejs
        echo "Node.js installed successfully."
    else
        echo "ERROR: Node.js setup failed!"
        exit 1
    fi
else
    echo "Node.js is already installed."
fi

echo "----------------------------------------------------------------"
echo "Setup complete!"
echo "IMPORTANT: You must log out and log back in (or reboot) for the"
echo "Docker group changes to take effect."
echo "----------------------------------------------------------------"
echo ""
read -p "Would you like to reboot now? (y/n): " answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
fi

exit 0
