#!/bin/bash
# Order API stress test for C# service using wrk with database writes
# This tests the BASELINE performance with MySQL transactions

set -e

# Configuration
URL="${1:-http://localhost:8082/api/v1/orders}"
THREADS="${2:-12}"
CONNECTIONS="${3:-100}"
DURATION="${4:-30s}"

echo "=========================================="
echo "C# Order API Stress Test (Baseline)"
echo "=========================================="
echo ""
echo "This test measures baseline order processing performance"
echo "with full database transactions (writes to orders, order_line_items, inventory)."
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

# Check if test data exists
if [ ! -f "/tmp/stress_test_sku_ids.txt" ]; then
    echo "ERROR: Test data not found!"
    echo ""
    echo "Please run setup first (from python-service directory):"
    echo "  cd ../python-service"
    echo "  python setup_test_data.py [num_spus] [skus_per_spu] [stock_per_sku]"
    echo ""
    echo "Example:"
    echo "  python setup_test_data.py 100 5 10000"
    echo "  (Creates 500 SKUs with 10,000 stock each)"
    echo ""
    exit 1
fi

# Count available SKUs
SKU_COUNT=$(wc -l < /tmp/stress_test_sku_ids.txt)
echo "Test Data:"
echo "  Available SKUs: $SKU_COUNT"
echo ""

# Check if server is responding
echo "Checking server status..."
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8082/health" || echo "000")
if [ "$HEALTH_CHECK" != "200" ]; then
    echo "WARNING: Server is not responding at http://localhost:8082/health"
    echo ""
    echo "Start the server with:"
    echo "  ./START_SERVER.sh"
    echo ""
    exit 1
fi

echo "✓ Server is running"
echo ""

# Check MariaDB max_connections
echo "Checking MariaDB connection limits..."
MAX_CONN=$(mysql -h 127.0.0.1 -P 3306 -u syracuse -pOrange_315_Forever! -e "SHOW VARIABLES LIKE 'max_connections';" 2>/dev/null | grep max_connections | awk '{print $2}')
if [ -n "$MAX_CONN" ]; then
    echo "  max_connections: $MAX_CONN"
    if [ "$MAX_CONN" -lt 200 ]; then
        echo "  ⚠️  Consider increasing max_connections"
    else
        echo "  ✓ Sufficient for stress testing"
    fi
else
    echo "  ⚠️  Could not check (MariaDB connection failed)"
fi
echo ""

# Check if Lua script exists
if [ ! -f "wrk_order_script.lua" ]; then
    echo "ERROR: wrk_order_script.lua not found"
    exit 1
fi

echo "Benchmark Configuration:"
echo "  Endpoint:     $URL"
echo "  Threads:      $THREADS"
echo "  Connections:  $CONNECTIONS"
echo "  Duration:     $DURATION"
echo ""
echo "Starting stress test..."
echo "This will create real orders in the database."
echo ""

# Run benchmark
wrk -t${THREADS} -c${CONNECTIONS} -d${DURATION} -s wrk_order_script.lua ${URL}

echo ""
echo "=========================================="
echo "Benchmark Complete"
echo "=========================================="
echo ""
echo "To analyze results:"
echo "  - Check database: mysql -h 127.0.0.1 -P 3306 -u syracuse -p orange315"
echo "    SELECT COUNT(*) FROM orders WHERE customer_email LIKE 'stress-test%';"
echo "    SELECT COUNT(*) FROM order_line_items;"
echo ""
echo "To clean test data (from python-service directory):"
echo "  cd ../python-service"
echo "  python setup_test_data.py 0 0 0  # Cleans without creating new data"
echo ""
echo "To run again with different settings:"
echo "  ./benchmark_orders.sh <url> <threads> <connections> <duration>"
echo "  Example: ./benchmark_orders.sh http://localhost:8082/api/v1/orders 24 200 60s"
echo ""
