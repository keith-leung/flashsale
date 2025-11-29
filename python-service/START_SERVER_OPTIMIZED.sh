#!/bin/bash
# Start server optimized for available CPU cores

echo "=========================================="
echo "Starting Optimized Uvicorn Server"
echo "=========================================="
echo ""

# Detect CPU cores
CPU_CORES=$(nproc)
echo "Detected CPU cores: $CPU_CORES"

# Calculate optimal workers
# For CPU-bound: workers = CPU cores
# For I/O-bound (our case): workers = 2 * CPU cores + 1
WORKERS=$((CPU_CORES * 2 + 1))

echo "Recommended workers for I/O-bound workload: $WORKERS"
echo ""

# Ask user which mode
echo "Select worker configuration:"
echo "  1) Conservative: $CPU_CORES workers (1 per core)"
echo "  2) Aggressive: $WORKERS workers (2x cores + 1) - RECOMMENDED"
echo "  3) Custom number"
echo ""
read -p "Enter choice [1-3] (default=2): " choice

case $choice in
    1)
        FINAL_WORKERS=$CPU_CORES
        ;;
    3)
        read -p "Enter number of workers: " FINAL_WORKERS
        ;;
    *)
        FINAL_WORKERS=$WORKERS
        ;;
esac

echo ""
echo "🚀 Starting with $FINAL_WORKERS workers"
echo "   This will utilize multiple CPU cores"
echo "   Press Ctrl+C to stop"
echo ""

# Kill any existing server
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

# Start server with optimal settings
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers $FINAL_WORKERS \
    --log-level info \
    --backlog 2048 \
    --limit-concurrency 10000 \
    --limit-max-requests 100000
