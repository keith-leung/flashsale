#!/bin/bash
# Test C# service /health endpoint

URL="${1:-http://localhost:8082/health}"
REQUESTS="${2:-1000}"
THREADS="${3:-12}"
CONNECTIONS="${4:-400}"
DURATION="${5:-30s}"

echo "=========================================="
echo "C# Service Health Endpoint Test"
echo "=========================================="
echo ""
echo "Testing endpoint: $URL"
echo ""

# Check if wrk is installed
if ! command -v wrk &> /dev/null; then
    echo "wrk not installed. Using curl for basic test..."
    echo ""

    # Basic curl test
    echo "Testing with curl:"
    time for i in {1..100}; do
        curl -s "$URL" > /dev/null
    done

    echo ""
    echo "100 requests completed"
    exit 0
fi

# Use wrk for performance test
echo "Running wrk benchmark:"
echo "  Threads: $THREADS"
echo "  Connections: $CONNECTIONS"
echo "  Duration: $DURATION"
echo ""

wrk -t${THREADS} -c${CONNECTIONS} -d${DURATION} ${URL}

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
