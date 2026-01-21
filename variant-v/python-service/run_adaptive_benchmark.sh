#!/bin/bash
# Run Adaptive Benchmark for Variant V with setup

set -e

echo "================================================"
echo "Variant V - Python Service - Setup & Benchmark"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "ERROR: Must run from variant-v/python-service directory"
    exit 1
fi

# Check for Docker (preferred, but not mandatory)
if ! command -v docker &> /dev/null; then
    echo "WARNING: Docker not found. Will try venv approach."
    echo ""
    HAS_DOCKER=false
else
    HAS_DOCKER=true
fi

if [ "$HAS_DOCKER" = true ]; then
    # Docker approach
    echo "Building Docker image..."
    docker build -t flashsale-v-python:latest .
    
    echo "Starting container..."
    docker run -d --name variant-v-python-test \
        -p 8000:8000 \
        flashsale-v-python:latest
    
    # Wait for startup
    echo "Waiting for service to start..."
    sleep 5
    
    echo ""
    echo "Running adaptive benchmark..."
    ./benchmark_adaptive.sh http://localhost:8000/health
    
    # Cleanup
    echo ""
    echo "Cleaning up container..."
    docker stop variant-v-python-test
    docker rm variant-v-python-test
    
else
    # Virtual environment approach
    echo "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        /usr/bin/python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    echo "Starting server in background..."
    python -m app.main > /tmp/variant_v_server.log 2>&1 &
    SERVER_PID=$!
    
    # Wait for startup
    echo "Waiting for service to start..."
    sleep 3
    
    echo ""
    echo "Running adaptive benchmark..."
    ./benchmark_adaptive.sh http://localhost:8000/health
    
    # Cleanup
    echo ""
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null
fi

echo ""
echo "================================================"
echo "Benchmark Complete!"
echo "================================================"
