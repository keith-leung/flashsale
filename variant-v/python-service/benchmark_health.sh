#!/bin/bash
# Health endpoint performance benchmark using wrk
# This is the primary benchmark tool for measuring maximum throughput

# Configuration
URL="${1:-http://localhost:8000/health}"
THREADS="${2:-12}"
CONNECTIONS="${3:-400}"
DURATION="${4:-30s}"

echo "=========================================="
echo "Variant V - Health Endpoint Benchmark"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  URL:         $URL"
echo "  Threads:     $THREADS"
echo "  Connections: $CONNECTIONS"
echo "  Duration:    $DURATION"
echo ""

# Check if wrk is installed
if ! command -v wrk &> /dev/null; then
    echo "ERROR: wrk is not installed"
    echo ""
    echo "Install with:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y wrk"
    echo ""
    exit 1
fi

# Check if server is responding
echo "Checking if server is responding..."
if ! curl -s -o /dev/null -w "%{http_code}" "$URL" | grep -q "200"; then
    echo "WARNING: Server at $URL is not responding with 200 OK"
    echo "Make sure the server is running:"
    echo "  cd /home/syracuse/flashsale/variant-v/python-service"
    echo "  python -m app.main"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Starting benchmark..."
echo ""

# Run benchmark with latency statistics
wrk -t${THREADS} -c${CONNECTIONS} -d${DURATION} --latency ${URL}

echo ""
echo "=========================================="
echo "Benchmark Complete"
echo "=========================================="
