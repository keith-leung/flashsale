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
# Workers = 2 * CPU cores + 1 (optimal for I/O-bound apps)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $(($(nproc) * 2 + 1)) --backlog 2048 --limit-concurrency 10000"]
