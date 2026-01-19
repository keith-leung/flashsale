FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy Poetry configuration
COPY requirements.txt .

# Install dependencies (using pip instead of poetry for simplicity)
RUN pip install --no-cache-dir -r requirements.txt

# Copy Lua script for atomic token acquisition
COPY acquire_order_token.lua /app/acquire_order_token.lua

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application with optimized settings for I/O-bound workload
# Workers = 16 (fixed to match Docker CPU allocation of 8 cores * 2)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 16 --backlog 2048 --limit-concurrency 10000"]