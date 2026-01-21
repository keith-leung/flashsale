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
COPY pyproject.toml .

# Configure poetry: no virtual env (we're in container), no interactive, cache deps
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application with optimized settings for I/O-bound workload
# Workers = 16 (fixed to match Docker CPU allocation of 8 cores * 2)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 16 --backlog 2048 --limit-concurrency 10000"]
