#!/bin/bash

# CherryPi - Raspberry Pi System Setup Script
# This script installs Docker and Node.js required for the project.

set -e  # Exit immediately if a command exits with a non-zero status.

echo "Starting CherryPi System Setup..."

# --- Docker Installation ---
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
    echo "Adding current user ($USER) to the docker group..."
    sudo usermod -aG docker $USER
    echo "Docker installed successfully."
else
    echo "Docker is already installed."
fi

# --- Node.js Installation ---
if ! command -v node &> /dev/null; then
    echo "Node.js not found. Installing Node.js (v18)..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo "Node.js installed successfully."
else
    echo "Node.js is already installed."
fi

echo "----------------------------------------------------------------"
echo "Setup complete!"
echo "IMPORTANT: You must log out and log back in (or restart) for the Docker group changes to take effect."
echo "----------------------------------------------------------------"
