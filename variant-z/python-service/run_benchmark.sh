#!/bin/bash
SKU_ID="2c2e23fa-f47b-4884-9b45-bf2a640f1ff3"
BASE_URL="http://localhost:30017"
TOTAL_REQUESTS=5000
CONCURRENCY=50

echo "========================================"
echo "Variant Z Python Service - Simple Benchmark"
echo "========================================"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Concurrency: $CONCURRENCY"
echo "SKU ID: $SKU_ID"
echo "========================================"
echo ""

# Health check
echo "1. Health Check..."
HEALTH=$(curl -s -w "%{http_code}" "$BASE_URL/health" 2>/dev/null)
if [ "$HEALTH" = "200200 OK" ]; then
    echo "   ✓ Health check passed"
else
    echo "   ✗ Health check failed"
    exit 1
fi
echo ""

# Run benchmark
echo "2. Running Benchmark..."
echo "   Sending $TOTAL_REQUESTS requests with $CONCURRENCY concurrent workers"
echo ""

START_TIME=$(date +%s)

# Run requests in background
for ((i=0; i<CONCURRENCY; i++)); do
    REQUESTS_PER_WORKER=$((TOTAL_REQUESTS / CONCURRENCY))
    (
        SUCCESS=0
        FAILED=0
        for ((j=0; j<REQUESTS_PER_WORKER; j++)); do
            RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/orders" \
                -H "Content-Type: application/json" \
                -d '{"customer_name": "Benchmark Customer", "customer_email": "benchmark@example.com", "line_items": [{"sku_id": "'"$SKU_ID"'", "quantity": 1}], "currency": "USD"}' 2>/dev/null)
            
            HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                SUCCESS=$((SUCCESS + 1))
            else
                FAILED=$((FAILED + 1))
            fi
        done
        echo "Worker $i: $SUCCESS successful, $FAILED failed"
    ) &
done

# Wait for all workers
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
RPS=$(echo "scale=2; $TOTAL_REQUESTS / $DURATION" | bc)

echo ""
echo "========================================"
echo "BENCHMARK RESULTS"
echo "========================================"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Duration: ${DURATION}s"
echo "Requests/sec: $RPS"
echo "========================================"
echo ""
echo "To verify data integrity:"
echo "  docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'"