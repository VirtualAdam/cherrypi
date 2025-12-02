FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for GPIO
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install Python dependencies
# Note: On non-Pi systems, rpi-rf will fail to import but won't crash the container
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir redis

# Copy all source files
COPY . .

# Create config directory and copy initial config if it doesn't exist
RUN mkdir -p /app/data

# Run main entry point that starts all services
CMD ["python", "main.py"]
