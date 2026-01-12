#!/bin/bash
# Performance Test for Python Order Processing - Variant A
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
CAMPAIGN_ID="perftest-camp-0000-0000-000000000001"
SKU_ID="perftest-sku1-0000-0000-000000000001"
URL="http://localhost:30013/api/v1/orders"

# Test parameters
PHASE1_ORDERS=10000   # Start with 10k for Phase 1
PHASE2_ORDERS=5000    # 5k for Phase 2
CONCURRENCY=50        # Concurrent requests

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════════"
echo "         Python Order Performance Test - Variant A"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Function to create order
create_order() {
    local order_num=$1
    local result=$(curl -s -w "\n%{http_code}\n%{time_total}" -X POST $URL \
        -H "Content-Type: application/json" \
        -d "{
            \"customer_email\": \"perftest${order_num}@example.com\",
            \"customer_name\": \"Perf Test ${order_num}\",
            \"line_items\": [{
                \"sku_id\": \"${SKU_ID}\",
                \"quantity\": 1
            }],
            \"flash_sale_campaign_id\": \"${CAMPAIGN_ID}\",
            \"currency\": \"USD\"
        }" 2>&1)

    local http_code=$(echo "$result" | tail -2 | head -1)
    local time_total=$(echo "$result" | tail -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "1 $time_total"
    else
        echo "0 $time_total"
    fi
}

export -f create_order
export URL CAMPAIGN_ID SKU_ID

# Function to run test phase
run_phase() {
    local phase_name="$1"
    local num_orders=$2
    local concurrency=$3
    local start_order=$4

    echo -e "\n${BOLD}${YELLOW}"
    echo "═══════════════════════════════════════════════════════════════════"
    echo "  ${phase_name}"
    echo "═══════════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo -e "${BLUE}Orders: ${num_orders}${NC}"
    echo -e "${BLUE}Concurrency: ${concurrency}${NC}"
    echo ""

    local successes=0
    local failures=0
    local total_time=0
    local start_time=$(date +%s.%N)

    # Run orders in parallel batches
    local batch_size=$((concurrency * 2))
    local completed=0

    while [ $completed -lt $num_orders ]; do
        local batch_count=$((num_orders - completed))
        if [ $batch_count -gt $batch_size ]; then
            batch_count=$batch_size
        fi

        # Create batch of orders in parallel
        for i in $(seq 0 $((batch_count - 1))); do
            create_order $((start_order + completed + i)) &
        done

        # Wait for batch to complete
        wait

        completed=$((completed + batch_count))

        # Progress update
        local elapsed=$(echo "$(date +%s.%N) - $start_time" | bc)
        local throughput=$(echo "$completed / $elapsed" | bc -l)

        if [ $((completed % 1000)) -eq 0 ] || [ $completed -eq $num_orders ]; then
            printf "\rProgress: %d/%d orders | Throughput: %.1f req/s" $completed $num_orders $throughput
        fi
    done

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)
    local throughput=$(echo "$num_orders / $duration" | bc -l)

    echo ""
    echo -e "\n${GREEN}✓ ${phase_name} completed${NC}"
    echo -e "${BLUE}Results:${NC}"
    echo -e "  Duration: ${duration}s"
    echo -e "  Orders: ${num_orders}"
    echo -e "  Throughput: ${BOLD}$(printf '%.2f' $throughput) req/s${NC}"

    echo "$throughput"
}

# Check service health
echo -e "${YELLOW}[Pre-check] Checking Python service...${NC}"
if curl -sf http://localhost:30013/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Python service ready${NC}"
else
    echo -e "${RED}✗ Python service not responding${NC}"
    exit 1
fi

# Mark log for Phase 1
LOGFILE="/var/log/flashsale/variant-a/orders_$(date +%Y%m%d).log"
docker exec flash-python-a sh -c "echo '>>> PHASE1_START $(date)' >> ${LOGFILE}" 2>/dev/null || true

# Phase 1: Pure in-memory
echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "PHASE 1: PURE IN-MEMORY (Best Case - No Redis Hits)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

PHASE1_THROUGHPUT=$(run_phase "Phase 1" $PHASE1_ORDERS $CONCURRENCY 1)

# Check Redis refills in Phase 1
REFILLS_PHASE1=$(docker exec flash-python-a sh -c "grep -c '\[SPU REFILL\]' ${LOGFILE} 2>/dev/null || echo 0")
echo -e "${BLUE}Redis Refills in Phase 1: ${REFILLS_PHASE1}${NC}"

# Mark log for Phase 2
docker exec flash-python-a sh -c "echo '>>> PHASE2_START $(date)' >> ${LOGFILE}" 2>/dev/null || true

# Phase 2: With Redis refills
echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "PHASE 2: WITH REDIS REFILLS (Degraded Performance)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

PHASE2_THROUGHPUT=$(run_phase "Phase 2" $PHASE2_ORDERS $CONCURRENCY $((PHASE1_ORDERS + 1)))

# Check Redis refills in Phase 2
REFILLS_PHASE2=$(docker exec flash-python-a sh -c "grep '\[SPU REFILL\]' ${LOGFILE} 2>/dev/null | grep -A 1 'PHASE2_START' | grep -c '\[SPU REFILL\]' || echo 0")
echo -e "${BLUE}Redis Refills in Phase 2: ${REFILLS_PHASE2}${NC}"

# Final Summary
echo -e "\n${BOLD}${GREEN}"
echo "═══════════════════════════════════════════════════════════════════"
echo "                   PERFORMANCE TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BOLD}Phase 1: Pure In-Memory${NC}"
echo -e "  Throughput: ${BOLD}${GREEN}$(printf '%.2f' $PHASE1_THROUGHPUT) req/s${NC}"
echo -e "  Redis Refills: ${REFILLS_PHASE1}"
echo ""

echo -e "${BOLD}Phase 2: With Redis Refills${NC}"
echo -e "  Throughput: ${BOLD}${YELLOW}$(printf '%.2f' $PHASE2_THROUGHPUT) req/s${NC}"
echo -e "  Redis Refills: ${REFILLS_PHASE2}"
echo ""

# Calculate degradation
DEGRADATION=$(echo "scale=2; (($PHASE1_THROUGHPUT - $PHASE2_THROUGHPUT) / $PHASE1_THROUGHPUT) * 100" | bc)
echo -e "${BOLD}Performance Impact:${NC}"
echo -e "  Redis Refill Overhead: ${BOLD}${RED}${DEGRADATION}%${NC} throughput reduction"

echo ""
echo -e "${BLUE}View Redis refill events:${NC}"
echo -e "  docker exec flash-python-a grep '\[SPU REFILL\]' ${LOGFILE}"

echo -e "\n${GREEN}✓ Performance test completed!${NC}"
