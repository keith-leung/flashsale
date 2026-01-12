#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# Python Order Performance Test - Variant A
# ═══════════════════════════════════════════════════════════════════
# This script tests Python service order processing performance with:
# - Phase 1: Pure in-memory (no Redis hits) - BEST CASE
# - Phase 2: With Redis refills (degraded) - REALISTIC CASE
#
# Campaign: perftest-camp-0000-0000-000000000001
# Local Cache: 176,470 items
# REFILL_BATCH_SIZE: 500
# ═══════════════════════════════════════════════════════════════════

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
PYTHON_URL="http://localhost:30013"

# Test parameters
PHASE1_ORDERS=150000  # Pure in-memory (below 176k cache)
PHASE2_ORDERS=50000   # With Redis refills
CONCURRENCY=100       # Concurrent requests
TOTAL_ORDERS=$((PHASE1_ORDERS + PHASE2_ORDERS))

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════════"
echo "         Python Order Performance Test - Variant A"
echo "           Testing Adaptive Inventory Performance"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Check Python service is running
echo -e "${YELLOW}[Pre-check] Verifying Python service...${NC}"
if ! curl -sf ${PYTHON_URL}/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Python service not responding${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python service ready${NC}"

# Check campaign status
echo -e "${YELLOW}[Pre-check] Checking campaign status...${NC}"
CAMPAIGN_STATUS=$(docker exec flash-python-a python3 << 'EOPY'
import asyncio
from app.services.campaign_memory_allocator import _campaign_allocator

status = _campaign_allocator.get_campaign_status('perftest-camp-0000-0000-000000000001')
if status:
    print(f"SPU_COUNTER={status['spu_counter']}")
    print(f"STATUS={status['status']}")
else:
    print("NOT_FOUND")
EOPY
)

if echo "$CAMPAIGN_STATUS" | grep -q "NOT_FOUND"; then
    echo -e "${RED}✗ Campaign not loaded in Python service${NC}"
    exit 1
fi

SPU_COUNTER=$(echo "$CAMPAIGN_STATUS" | grep "SPU_COUNTER" | cut -d'=' -f2)
echo -e "${GREEN}✓ Campaign loaded: ${SPU_COUNTER} items in local cache${NC}"

# Clear previous log markers
LOGFILE="/var/log/flashsale/variant-a/orders_$(date +%Y%m%d).log"
MARKER_FILE="/tmp/perf_test_marker_$(date +%s).log"

echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Phase 1: PURE IN-MEMORY Performance (Best Case)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "${BLUE}Target: ${PHASE1_ORDERS} orders${NC}"
echo -e "${BLUE}Expected: NO Redis hits (all from local cache)${NC}"
echo -e "${BLUE}Concurrency: ${CONCURRENCY}${NC}"
echo ""

# Create payload file for wrk
cat > /tmp/order_payload.lua << 'EOLUA'
counter = 0

request = function()
   counter = counter + 1
   local email = string.format("perftest%d@example.com", counter)
   local name = string.format("Perf Test User %d", counter)

   local body = string.format([[{
      "customer_email": "%s",
      "customer_name": "%s",
      "line_items": [{
         "sku_id": "perftest-sku1-0000-0000-000000000001",
         "quantity": 1
      }],
      "flash_sale_campaign_id": "perftest-camp-0000-0000-000000000001",
      "currency": "USD"
   }]], email, name)

   return wrk.format("POST", "/api/v1/orders",
      {["Content-Type"] = "application/json"}, body)
end
EOLUA

# Mark log before Phase 1
echo -e "${YELLOW}Marking logs for Phase 1 start...${NC}"
docker exec flash-python-a sh -c "echo '>>> PHASE1_START' >> ${LOGFILE}"

# Run Phase 1: Pure in-memory
echo -e "${YELLOW}Running Phase 1 test...${NC}"
START_TIME=$(date +%s)

wrk -t ${CONCURRENCY} -c ${CONCURRENCY} -d $((PHASE1_ORDERS / 1000))s \
    -s /tmp/order_payload.lua \
    --latency \
    http://localhost:30013/api/v1/orders \
    > /tmp/phase1_results.txt 2>&1

PHASE1_END=$(date +%s)
PHASE1_DURATION=$((PHASE1_END - START_TIME))

# Parse Phase 1 results
PHASE1_REQUESTS=$(grep "requests in" /tmp/phase1_results.txt | awk '{print $1}')
PHASE1_THROUGHPUT=$(grep "Requests/sec:" /tmp/phase1_results.txt | awk '{print $2}')
PHASE1_LATENCY_AVG=$(grep "Latency" /tmp/phase1_results.txt | head -1 | awk '{print $2}')
PHASE1_LATENCY_P99=$(grep "99%" /tmp/phase1_results.txt | awk '{print $2}')

echo -e "${GREEN}✓ Phase 1 completed${NC}"
echo -e "${BLUE}Results:${NC}"
echo -e "  Requests: ${PHASE1_REQUESTS}"
echo -e "  Throughput: ${BOLD}${PHASE1_THROUGHPUT} req/s${NC}"
echo -e "  Latency (avg): ${PHASE1_LATENCY_AVG}"
echo -e "  Latency (p99): ${PHASE1_LATENCY_P99}"

# Check if any Redis refills happened in Phase 1
echo -e "\n${YELLOW}Checking for Redis refills in Phase 1...${NC}"
REDIS_REFILLS_PHASE1=$(docker exec flash-python-a sh -c "grep -c '\[SPU REFILL\]' ${LOGFILE} || echo 0")

if [ "$REDIS_REFILLS_PHASE1" -eq 0 ]; then
    echo -e "${GREEN}✓ NO Redis refills - Pure in-memory performance confirmed!${NC}"
else
    echo -e "${YELLOW}⚠ ${REDIS_REFILLS_PHASE1} Redis refills detected in Phase 1${NC}"
    echo -e "${YELLOW}  (Cache exhausted earlier than expected)${NC}"
fi

# Phase 2: With Redis refills
echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Phase 2: WITH REDIS REFILLS (Degraded Performance)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "${BLUE}Target: ${PHASE2_ORDERS} additional orders${NC}"
echo -e "${BLUE}Expected: Redis refills triggered (REFILL_BATCH_SIZE=500)${NC}"
echo -e "${BLUE}Concurrency: ${CONCURRENCY}${NC}"
echo ""

# Mark log before Phase 2
docker exec flash-python-a sh -c "echo '>>> PHASE2_START' >> ${LOGFILE}"

echo -e "${YELLOW}Running Phase 2 test...${NC}"
PHASE2_START=$(date +%s)

wrk -t ${CONCURRENCY} -c ${CONCURRENCY} -d $((PHASE2_ORDERS / 1000))s \
    -s /tmp/order_payload.lua \
    --latency \
    http://localhost:30013/api/v1/orders \
    > /tmp/phase2_results.txt 2>&1

PHASE2_END=$(date +%s)
PHASE2_DURATION=$((PHASE2_END - PHASE2_START))

# Parse Phase 2 results
PHASE2_REQUESTS=$(grep "requests in" /tmp/phase2_results.txt | awk '{print $1}')
PHASE2_THROUGHPUT=$(grep "Requests/sec:" /tmp/phase2_results.txt | awk '{print $2}')
PHASE2_LATENCY_AVG=$(grep "Latency" /tmp/phase2_results.txt | head -1 | awk '{print $2}')
PHASE2_LATENCY_P99=$(grep "99%" /tmp/phase2_results.txt | awk '{print $2}')

echo -e "${GREEN}✓ Phase 2 completed${NC}"
echo -e "${BLUE}Results:${NC}"
echo -e "  Requests: ${PHASE2_REQUESTS}"
echo -e "  Throughput: ${BOLD}${PHASE2_THROUGHPUT} req/s${NC}"
echo -e "  Latency (avg): ${PHASE2_LATENCY_AVG}"
echo -e "  Latency (p99): ${PHASE2_LATENCY_P99}"

# Count Redis refills in Phase 2
echo -e "\n${YELLOW}Checking Redis refills in Phase 2...${NC}"
REDIS_REFILLS_PHASE2=$(docker exec flash-python-a sh -c "grep '\[SPU REFILL\]' ${LOGFILE} | grep -v 'PHASE1' | wc -l")

if [ "$REDIS_REFILLS_PHASE2" -gt 0 ]; then
    echo -e "${GREEN}✓ ${REDIS_REFILLS_PHASE2} Redis refills triggered as expected${NC}"
else
    echo -e "${YELLOW}⚠ No Redis refills in Phase 2 (unexpected)${NC}"
fi

# Final Summary
echo -e "\n${BOLD}${GREEN}"
echo "═══════════════════════════════════════════════════════════════════"
echo "                   Performance Test Summary"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BOLD}Phase 1: Pure In-Memory (Best Case)${NC}"
echo -e "  Throughput: ${BOLD}${GREEN}${PHASE1_THROUGHPUT} req/s${NC}"
echo -e "  Latency (avg): ${PHASE1_LATENCY_AVG}"
echo -e "  Latency (p99): ${PHASE1_LATENCY_P99}"
echo -e "  Redis Refills: ${REDIS_REFILLS_PHASE1}"
echo ""

echo -e "${BOLD}Phase 2: With Redis Refills (Degraded)${NC}"
echo -e "  Throughput: ${BOLD}${YELLOW}${PHASE2_THROUGHPUT} req/s${NC}"
echo -e "  Latency (avg): ${PHASE2_LATENCY_AVG}"
echo -e "  Latency (p99): ${PHASE2_LATENCY_P99}"
echo -e "  Redis Refills: ${REDIS_REFILLS_PHASE2}"
echo ""

# Calculate degradation
if [ -n "$PHASE1_THROUGHPUT" ] && [ -n "$PHASE2_THROUGHPUT" ]; then
    DEGRADATION=$(awk "BEGIN {printf \"%.1f\", (1 - ${PHASE2_THROUGHPUT}/${PHASE1_THROUGHPUT}) * 100}")
    echo -e "${BOLD}Performance Impact:${NC}"
    echo -e "  Redis Refill Overhead: ${BOLD}${RED}${DEGRADATION}%${NC} throughput reduction"
fi

echo ""
echo -e "${BLUE}Detailed logs:${NC}"
echo -e "  docker exec flash-python-a cat ${LOGFILE}"
echo -e "  docker exec flash-python-a grep '\[SPU REFILL\]' ${LOGFILE}"

echo -e "\n${GREEN}✓ Performance test completed successfully!${NC}"
