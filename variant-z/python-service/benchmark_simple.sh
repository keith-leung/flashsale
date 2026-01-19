#!/bin/bash
# Simple benchmark script for Variant Z Python service
# Tests both health and order creation endpoints

set -e

BASE_URL="${1:-http://localhost:30017}"
DURATION="${2:-30}"
CONCURRENCY="${3:-100}"

echo "=========================================="
echo "Variant Z Python Service - Simple Benchmark"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Duration: ${DURATION}s"
echo "Concurrency: $CONCURRENCY"
echo "=========================================="
echo ""

# Check if service is running
echo "1. Health Check..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/health" 2>/dev/null || echo "000")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n-1)

if [ "$HEALTH_CODE" = "200" ] && [ "$HEALTH_BODY" = "200 OK" ]; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed (HTTP $HEALTH_CODE)"
    echo "Response: $HEALTH_BODY"
    exit 1
fi
echo ""

# Get SKU ID from test data
echo "2. Getting test SKU ID..."
SKU_INFO=$(docker exec flash-python-z python -c "
import asyncio
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.spu import SPU
from app.models.sku import SKU

async def get_sku():
    async with async_session_maker() as session:
        result = await session.execute(
            select(SKU).join(SPU).where(SPU.slug == 'flash-sale-test-product')
        )
        sku = result.scalar_one_or_none()
        if sku:
            print(sku.id)
        else:
            print('NOT_FOUND')

asyncio.run(get_sku())
" 2>/dev/null || echo "NOT_FOUND")

if [ "$SKU_INFO" = "NOT_FOUND" ] || [ -z "$SKU_INFO" ]; then
    echo "✗ Test SKU not found. Please run setup_test_data.py first"
    exit 1
fi

SKU_ID=$(echo "$SKU_INFO" | tr -d '\r\n')
echo "✓ Found SKU ID: $SKU_ID"
echo ""

# Create wrk script for order creation
cat > /tmp/benchmark_orders.lua << 'EOF'
-- wrk script for benchmarking order creation
wrk.method = "POST"
wrk.body   = '{"customer_name": "Benchmark Customer", "customer_email": "benchmark@example.com", "line_items": [{"sku_id": "' .. os.getenv("SKU_ID") .. '", "quantity": 1}], "currency": "USD"}'
wrk.headers["Content-Type"] = "application/json"

function response(status, headers, body)
    if status == 200 or status == 201 then
        responses_ok = responses_ok + 1
    else
        responses_error = responses_error + 1
    end
end

function done(summary, latency, requests)
    print("\n=== Response Breakdown ===")
    print(string.format("Successful (200/201): %d", responses_ok or 0))
    print(string.format("Errors (4xx/5xx): %d", responses_error or 0))
end
EOF

# Export SKU_ID for the wrk script
export SKU_ID="$SKU_ID"

# Check if wrk is installed
if ! command -v wrk &> /dev/null; then
    echo "⚠ wrk not found. Installing wrk..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y wrk
    elif command -v brew &> /dev/null; then
        brew install wrk
    else
        echo "✗ Cannot install wrk automatically. Please install wrk manually."
        echo "  Ubuntu/Debian: sudo apt-get install wrk"
        echo "  macOS: brew install wrk"
        exit 1
    fi
fi

# Run benchmark
echo "3. Running Order Creation Benchmark..."
echo "   This will test the token pre-allocation system"
echo "   Target: 3,000+ req/s"
echo ""

wrk -t4 -c"$CONCURRENCY" -d"${DURATION}s" -s /tmp/benchmark_orders.lua \
    "$BASE_URL/api/v1/orders" 2>&1 || true

echo ""
echo "=========================================="
echo "Benchmark Complete!"
echo "=========================================="
echo ""
echo "Key Metrics to Check:"
echo "  - Requests/sec: Should be >3,000 for Variant Z"
echo "  - Latency avg: Should be <50ms"
echo "  - Errors: Should be 0 (until tokens exhausted)"
echo ""
echo "To verify data integrity:"
echo "  docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'"
echo "  docker exec flash-redis-z redis-cli ZCARD campaign:{campaign_id}:tokens"
echo ""

# Cleanup
rm -f /tmp/benchmark_orders.lua