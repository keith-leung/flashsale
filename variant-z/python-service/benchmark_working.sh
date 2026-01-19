#!/bin/bash
# Simple working benchmark for Variant Z Python service

SKU_ID="2c2e23fa-f47b-4884-9b45-bf2a640f1ff3"
BASE_URL="http://localhost:30017"
TOTAL_REQUESTS=1000
CONCURRENCY=50

echo "========================================"
echo "Variant Z Python Service - Benchmark"
echo "========================================"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Concurrency: $CONCURRENCY"
echo "========================================"
echo ""

# Health check
echo "1. Health Check..."
HEALTH=$(curl -s "$BASE_URL/health")
if [ "$HEALTH" = "200 OK" ]; then
    echo "   ✓ Health check passed"
else
    echo "   ✗ Health check failed"
    exit 1
fi
echo ""

# Run benchmark
echo "2. Running Benchmark..."
START_TIME=$(date +%s)

# Run requests in background
SUCCESS=0
FAILED=0

for ((i=0; i<CONCURRENCY; i++)); do
    (
        REQUESTS_PER_WORKER=$((TOTAL_REQUESTS / CONCURRENCY))
        WORKER_SUCCESS=0
        WORKER_FAILED=0
        
        for ((j=0; j<REQUESTS_PER_WORKER; j++)); do
            RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/orders/" \
                -H "Content-Type: application/json" \
                -d '{"customer_name": "Benchmark Customer", "customer_email": "benchmark@example.com", "line_items": [{"sku_id": "'"$SKU_ID"'", "quantity": 1}], "currency": "USD"}' 2>/dev/null)
            
            HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                WORKER_SUCCESS=$((WORKER_SUCCESS + 1))
            else
                WORKER_FAILED=$((WORKER_FAILED + 1))
            fi
        done
        
        echo "Worker $i: $WORKER_SUCCESS successful, $WORKER_FAILED failed"
    ) &
done

# Wait for all workers
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "========================================"
echo "BENCHMARK RESULTS"
echo "========================================"
echo "Total Requests: $TOTAL_REQUESTS"
echo "Duration: ${DURATION}s"

if [ $DURATION -gt 0 ]; then
    RPS=$(echo "scale=2; $TOTAL_REQUESTS / $DURATION" | bc)
    echo "Requests/sec: $RPS"
fi

echo "========================================"
echo ""
echo "To verify data integrity:"
echo "  docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'"