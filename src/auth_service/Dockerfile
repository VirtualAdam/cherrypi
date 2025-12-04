FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create data directory for encrypted database
RUN mkdir -p /data

# Environment variables (should be overridden in docker-compose)
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV AUTH_DATA_DIR=/data

# Run the auth service
CMD ["python", "auth_service.py"]
