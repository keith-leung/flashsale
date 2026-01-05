#!/bin/bash
# =============================================================================
# Variant A Performance Test
# =============================================================================
# Tests Variant A adaptive inventory implementation and compares with Variant Y
#
# Exit codes:
#   0 = Test completed successfully
#   1 = Test failed
# =============================================================================

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./results"
CSV_FILE="${RESULTS_DIR}/variant_A_test_${TIMESTAMP}.csv"

echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "                   Variant A Performance Test"
echo "            Adaptive Inventory with 2-Tier Batching"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "${BLUE}Timestamp: ${TIMESTAMP}${NC}"
echo -e "${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

# =============================================================================
# Step 1: Verify Services Running
# =============================================================================
echo -e "${YELLOW}[Step 1/4] Verifying Variant A services...${NC}"

CONTAINERS=("flash-mariadb-a" "flash-redis-a" "flash-python-a")
ALL_RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        STATUS=$(docker ps --filter "name=^${container}$" --format "{{.Status}}")
        echo -e "${GREEN}  ✓ ${container}: ${STATUS}${NC}"
    else
        echo -e "${RED}  ✗ ${container}: NOT RUNNING${NC}"
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo -e "${RED}Test failed: Not all services running${NC}"
    exit 1
fi

# =============================================================================
# Step 2: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 2/4] Running health checks...${NC}"

if curl -sf http://localhost:30013/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Python health OK${NC}"
else
    echo -e "${RED}✗ Python health FAILED${NC}"
    exit 1
fi

# =============================================================================
# Step 3: Setup Test Campaign
# =============================================================================
echo -e "\n${YELLOW}[Step 3/4] Setting up test campaign...${NC}"

# Check if campaign exists
CAMPAIGN_COUNT=$(docker exec flash-mariadb-a mysql -usyracuse -pOrange_315_Forever! orange315 -e "SELECT COUNT(*) FROM flash_sale_campaigns WHERE id='750e8400-e29b-41d4-a716-446655440000'" 2>&1 | tail -1)

if [ "$CAMPAIGN_COUNT" -eq 0 ]; then
    echo -e "${BLUE}Creating test campaign (10,000 inventory)...${NC}"

    docker exec flash-mariadb-a mysql -usyracuse -pOrange_315_Forever! orange315 <<'EOF'
INSERT IGNORE INTO spus (id, name, description, is_active, created_at, updated_at)
VALUES ('650e8400-e29b-41d4-a716-446655440000', 'Test Product A Benchmark', 'Benchmark product', 1, NOW(), NOW());

INSERT IGNORE INTO skus (id, spu_id, sku_code, name, price, track_inventory, is_active, created_at, updated_at)
VALUES ('650e8400-e29b-41d4-a716-446655440001', '650e8400-e29b-41d4-a716-446655440000', 'BENCH-SKU-A1', 'Benchmark SKU A1', 99.99, 1, 1, NOW(), NOW());

DELETE FROM inventory WHERE sku_id = '650e8400-e29b-41d4-a716-446655440001';
INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at)
VALUES (UUID(), '650e8400-e29b-41d4-a716-446655440001', 1000000, 0, 0, NOW(), NOW());

INSERT IGNORE INTO flash_sale_campaigns (id, name, description, spu_id, total_sale_limit, sold_quantity, max_quantity_per_customer, flash_price, start_time, end_time, status, is_active, created_at, updated_at)
VALUES ('750e8400-e29b-41d4-a716-446655440000', 'Variant A Benchmark Campaign', 'Benchmark test', '650e8400-e29b-41d4-a716-446655440000', 1000000, 0, 100, 79.99, '2025-01-01 00:00:00', '2030-12-31 23:59:59', 'active', 1, NOW(), NOW());
EOF

    # Initialize Redis with 1M inventory
    docker exec flash-redis-a redis-cli SET "fs:750e8400-e29b-41d4-a716-446655440000:sku:650e8400-e29b-41d4-a716-446655440001:limit" 1000000 > /dev/null

    echo -e "${GREEN}✓ Campaign created with 1,000,000 inventory${NC}"
else
    echo -e "${GREEN}✓ Campaign already exists${NC}"

    # Reset Redis counter to 1M
    docker exec flash-redis-a redis-cli SET "fs:750e8400-e29b-41d4-a716-446655440000:sku:650e8400-e29b-41d4-a716-446655440001:limit" 1000000 > /dev/null
    echo -e "${GREEN}✓ Redis counter reset to 1,000,000${NC}"
fi

# =============================================================================
# Step 4: Run Benchmarks
# =============================================================================
echo -e "\n${YELLOW}[Step 4/4] Running order processing benchmarks...${NC}"

mkdir -p "$RESULTS_DIR"

# Initialize CSV
cat > "$CSV_FILE" << 'EOF'
variant,service,endpoint,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p99_latency_ms,total_requests,errors,mode_notes
EOF

echo -e "\n${BLUE}Testing Python order endpoint with adaptive inventory...${NC}"

# Test different concurrency levels
for CONCURRENCY in 10 25 50 100 150; do
    echo -e "\n${BLUE}Testing c=${CONCURRENCY}...${NC}"

    # Record Redis counter before
    REDIS_BEFORE=$(docker exec flash-redis-a redis-cli GET "fs:750e8400-e29b-41d4-a716-446655440000:sku:650e8400-e29b-41d4-a716-446655440001:limit")

    # Calculate threads (must be <= connections)
    THREADS=$((CONCURRENCY < 12 ? CONCURRENCY : 12))

    # Run wrk test
    WRK_OUTPUT=$(wrk -t${THREADS} -c${CONCURRENCY} -d10s -s /tmp/variant_a_bench.lua http://localhost:30013/api/v1/orders 2>&1)

    # Record Redis counter after
    REDIS_AFTER=$(docker exec flash-redis-a redis-cli GET "fs:750e8400-e29b-41d4-a716-446655440000:sku:650e8400-e29b-41d4-a716-446655440001:limit")

    # Calculate Redis calls
    REDIS_DIFF=$((REDIS_BEFORE - REDIS_AFTER))

    # Parse wrk output
    REQ_SEC=$(echo "$WRK_OUTPUT" | grep "Requests/sec:" | awk '{print $2}')
    AVG_LAT=$(echo "$WRK_OUTPUT" | grep "Latency" | head -1 | awk '{print $2}' | sed 's/ms//')
    P50_LAT=$(echo "$WRK_OUTPUT" | grep "50%" | awk '{print $2}' | sed 's/ms//' | sed 's/us//' | awk '{if ($1 < 100) print $1/1000; else print $1}')
    P99_LAT=$(echo "$WRK_OUTPUT" | grep "99%" | awk '{print $2}' | sed 's/ms//' | sed 's/us//' | awk '{if ($1 < 100) print $1/1000; else print $1}')
    TOTAL_REQ=$(echo "$WRK_OUTPUT" | grep "requests in" | awk '{print $1}')
    ERRORS=$(echo "$WRK_OUTPUT" | grep "Non-2xx" | awk '{print $4}' || echo "0")

    # Determine mode
    if [ "$REDIS_DIFF" -eq 0 ]; then
        MODE="BATCH_MODE_active_local_cache"
    elif [ "$REDIS_DIFF" -eq 500 ]; then
        MODE="BATCH_MODE_refilled_once"
    else
        MODE="Redis_decremented_by_${REDIS_DIFF}"
    fi

    # Write to CSV
    echo "variant_a,python,/api/v1/orders,${CONCURRENCY},10,${REQ_SEC},${AVG_LAT},${P50_LAT},${P99_LAT},${TOTAL_REQ},${ERRORS},${MODE}" >> "$CSV_FILE"

    echo -e "${GREEN}  c=${CONCURRENCY}: ${REQ_SEC} req/s, Redis: ${REDIS_BEFORE}→${REDIS_AFTER} (${MODE})${NC}"

    # Sleep between tests
    sleep 2
done

# =============================================================================
# Generate Comparison Report
# =============================================================================
echo -e "\n${YELLOW}Generating comparison report...${NC}"

# Best result from Variant A
BEST_A=$(tail -n +2 "$CSV_FILE" | sort -t',' -k6 -n -r | head -1)
BEST_A_RPS=$(echo "$BEST_A" | cut -d',' -f6)
BEST_A_CONCURRENCY=$(echo "$BEST_A" | cut -d',' -f4)

# Variant Y best result (from SACRED VERIFICATION)
VARIANT_Y_PYTHON_RPS=960.16
VARIANT_Y_JAVA_RPS=5835.94
VARIANT_Y_CSHARP_RPS=4537.00

# Calculate improvement
IMPROVEMENT=$(echo "scale=1; (($BEST_A_RPS - $VARIANT_Y_PYTHON_RPS) / $VARIANT_Y_PYTHON_RPS) * 100" | bc)

echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "              Variant A vs Variant Y Comparison"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BLUE}Python Order Processing:${NC}"
echo -e "  Variant Y: ${VARIANT_Y_PYTHON_RPS} req/s @ c=57"
echo -e "  Variant A: ${BEST_A_RPS} req/s @ c=${BEST_A_CONCURRENCY}"
if (( $(echo "$IMPROVEMENT > 0" | bc -l) )); then
    echo -e "  ${GREEN}Improvement: +${IMPROVEMENT}% 🚀${NC}"
else
    echo -e "  ${RED}Performance: ${IMPROVEMENT}%${NC}"
fi

echo -e "\n${BLUE}Results saved to:${NC}"
echo -e "  ${CSV_FILE}"

echo -e "\n${GREEN}✓ Variant A test completed successfully${NC}"
exit 0
