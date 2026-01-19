#!/bin/bash
# Start Variant Z Python Service

set -e

echo "=========================================="
echo "Starting Variant Z Python Service"
echo "Token Pre-Allocation Architecture"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running"
    exit 1
fi

# Start the Python service
echo "Starting Python service container..."
docker-compose up -d python-service

echo "Waiting for service to be ready..."
sleep 5

# Check health
echo "Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost:30017/health | grep -q "200 OK"; then
        echo "✓ Service is healthy!"
        echo ""
        echo "Service URL: http://localhost:30017"
        echo "Health Check: http://localhost:30017/health"
        echo "API Docs: http://localhost:30017/docs"
        echo ""
        echo "To initialize database and test data, run:"
        echo "  docker exec flash-python-z python init_db.py"
        echo "  docker exec flash-python-z python setup_test_data.py"
        echo ""
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 2
done

echo "=========================================="
echo "Variant Z Python Service Started"
echo "=========================================="