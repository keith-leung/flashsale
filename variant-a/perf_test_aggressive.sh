#!/bin/bash
# Aggressive Performance Test - Will trigger Redis refills
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

CAMPAIGN_ID="perftest-camp-0000-0000-000000000001"
SKU_ID="perftest-sku1-0000-0000-000000000001"
URL="http://localhost:30013/api/v1/orders"

# Aggressive settings - Will exhaust 176k cache and trigger refills
PHASE1_ORDERS=170000  # Close to cache limit - pure in-memory
PHASE2_ORDERS=30000   # Will trigger Redis refills
CONCURRENCY=100

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════════"
echo "         AGGRESSIVE Python Order Performance Test"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo "Phase 1: 170,000 orders (pure in-memory)"
echo "Phase 2: 30,000 orders (will trigger Redis refills)"
echo "Local Cache: 176,470 items"
echo ""

# Test order creation
test_single_order() {
    curl -s -X POST $URL \
        -H "Content-Type: application/json" \
        -d "{
            \"customer_email\": \"test@example.com\",
            \"customer_name\": \"Test\",
            \"line_items\": [{\"sku_id\": \"${SKU_ID}\", \"quantity\": 1}],
            \"flash_sale_campaign_id\": \"${CAMPAIGN_ID}\",
            \"currency\": \"USD\"
        }" > /dev/null 2>&1

    echo $?
}

echo -e "${YELLOW}[Pre-check] Testing single order...${NC}"
if [ "$(test_single_order)" = "0" ]; then
    echo -e "${GREEN}✓ Order creation working${NC}"
else
    echo -e "${RED}✗ Order creation failed${NC}"
    exit 1
fi

# Mark test start
LOGFILE="/var/log/flashsale/variant-a/orders_$(date +%Y%m%d).log"
docker exec flash-python-a sh -c "echo '>>> AGGRESSIVE_PHASE1_START $(date +%s)' >> ${LOGFILE}" 2>/dev/null || true

echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Phase 1: 170K Orders (Pure In-Memory)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

PHASE1_START=$(date +%s)

# Use GNU parallel if available, otherwise use xargs
if command -v parallel >/dev/null 2>&1; then
    seq 1 $PHASE1_ORDERS | parallel -j $CONCURRENCY --bar "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"customer_email\":\"p1test{}@ex.com\",\"customer_name\":\"P1 Test {}\",\"line_items\":[{\"sku_id\":\"${SKU_ID}\",\"quantity\":1}],\"flash_sale_campaign_id\":\"${CAMPAIGN_ID}\",\"currency\":\"USD\"}' > /dev/null 2>&1"
else
    echo "Creating 170,000 orders with concurrency ${CONCURRENCY}..."
    echo "This will take approximately 15-30 minutes..."

    # Batch processing with xargs
    seq 1 $PHASE1_ORDERS | xargs -P $CONCURRENCY -I {} bash -c "
        curl -s -X POST $URL \
            -H 'Content-Type: application/json' \
            -d '{\"customer_email\":\"p1test{}@ex.com\",\"customer_name\":\"P1 Test {}\",\"line_items\":[{\"sku_id\":\"${SKU_ID}\",\"quantity\":1}],\"flash_sale_campaign_id\":\"${CAMPAIGN_ID}\",\"currency\":\"USD\"}' \
            > /dev/null 2>&1

        # Progress indicator every 1000 orders
        if [ \$(( {} % 1000 )) -eq 0 ]; then
            echo -ne \"\rProgress: {}/${PHASE1_ORDERS}\"
        fi
    "
fi

PHASE1_END=$(date +%s)
PHASE1_DURATION=$((PHASE1_END - PHASE1_START))
PHASE1_THROUGHPUT=$(awk "BEGIN {printf \"%.2f\", $PHASE1_ORDERS / $PHASE1_DURATION}")

echo -e "\n${GREEN}✓ Phase 1 completed${NC}"
echo -e "${BLUE}Duration: ${PHASE1_DURATION}s${NC}"
echo -e "${BLUE}Throughput: ${BOLD}${PHASE1_THROUGHPUT} req/s${NC}"

# Check refills
REFILLS_PHASE1=$(docker exec flash-python-a sh -c "grep -c '\[SPU REFILL\]' ${LOGFILE} 2>/dev/null || echo 0")
echo -e "${BLUE}Redis Refills: ${REFILLS_PHASE1}${NC}"

# Mark Phase 2 start
docker exec flash-python-a sh -c "echo '>>> AGGRESSIVE_PHASE2_START $(date +%s)' >> ${LOGFILE}" 2>/dev/null || true

echo -e "\n${BOLD}${YELLOW}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  Phase 2: 30K Orders (With Redis Refills)"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

PHASE2_START=$(date +%s)

if command -v parallel >/dev/null 2>&1; then
    seq $((PHASE1_ORDERS + 1)) $((PHASE1_ORDERS + PHASE2_ORDERS)) | parallel -j $CONCURRENCY --bar "curl -s -X POST $URL -H 'Content-Type: application/json' -d '{\"customer_email\":\"p2test{}@ex.com\",\"customer_name\":\"P2 Test {}\",\"line_items\":[{\"sku_id\":\"${SKU_ID}\",\"quantity\":1}],\"flash_sale_campaign_id\":\"${CAMPAIGN_ID}\",\"currency\":\"USD\"}' > /dev/null 2>&1"
else
    echo "Creating 30,000 orders..."
    seq $((PHASE1_ORDERS + 1)) $((PHASE1_ORDERS + PHASE2_ORDERS)) | xargs -P $CONCURRENCY -I {} bash -c "
        curl -s -X POST $URL \
            -H 'Content-Type: application/json' \
            -d '{\"customer_email\":\"p2test{}@ex.com\",\"customer_name\":\"P2 Test {}\",\"line_items\":[{\"sku_id\":\"${SKU_ID}\",\"quantity\":1}],\"flash_sale_campaign_id\":\"${CAMPAIGN_ID}\",\"currency\":\"USD\"}' \
            > /dev/null 2>&1

        if [ \$(( {} % 1000 )) -eq 0 ]; then
            echo -ne \"\rProgress: \$(( {} - $PHASE1_ORDERS ))/${PHASE2_ORDERS}\"
        fi
    "
fi

PHASE2_END=$(date +%s)
PHASE2_DURATION=$((PHASE2_END - PHASE2_START))
PHASE2_THROUGHPUT=$(awk "BEGIN {printf \"%.2f\", $PHASE2_ORDERS / $PHASE2_DURATION}")

echo -e "\n${GREEN}✓ Phase 2 completed${NC}"
echo -e "${BLUE}Duration: ${PHASE2_DURATION}s${NC}"
echo -e "${BLUE}Throughput: ${BOLD}${PHASE2_THROUGHPUT} req/s${NC}"

# Count total refills
REFILLS_TOTAL=$(docker exec flash-python-a sh -c "grep -c '\[SPU REFILL\]' ${LOGFILE} 2>/dev/null || echo 0")
REFILLS_PHASE2=$((REFILLS_TOTAL - REFILLS_PHASE1))
echo -e "${BLUE}Redis Refills: ${REFILLS_PHASE2}${NC}"

# Final Summary
echo -e "\n${BOLD}${GREEN}"
echo "═══════════════════════════════════════════════════════════════════"
echo "                   PERFORMANCE TEST SUMMARY"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BOLD}Phase 1: Pure In-Memory (170K orders)${NC}"
echo -e "  Throughput: ${BOLD}${GREEN}${PHASE1_THROUGHPUT} req/s${NC}"
echo -e "  Duration: ${PHASE1_DURATION}s"
echo -e "  Redis Refills: ${REFILLS_PHASE1}"
echo ""

echo -e "${BOLD}Phase 2: With Redis Refills (30K orders)${NC}"
echo -e "  Throughput: ${BOLD}${YELLOW}${PHASE2_THROUGHPUT} req/s${NC}"
echo -e "  Duration: ${PHASE2_DURATION}s"
echo -e "  Redis Refills: ${REFILLS_PHASE2}"
echo ""

if [ "$PHASE1_THROUGHPUT" != "0" ] && [ "$PHASE2_THROUGHPUT" != "0" ]; then
    DEGRADATION=$(awk "BEGIN {printf \"%.1f\", (($PHASE1_THROUGHPUT - $PHASE2_THROUGHPUT) / $PHASE1_THROUGHPUT) * 100}")
    echo -e "${BOLD}Performance Impact:${NC}"
    echo -e "  Redis Refill Overhead: ${BOLD}${RED}${DEGRADATION}%${NC} throughput reduction"
fi

# Verify orders in DB
TOTAL_ORDERS=$(docker exec flash-mariadb-a mysql -uroot -proot orange315 -e "SELECT COUNT(*) FROM orders WHERE flash_sale_campaign_id = '${CAMPAIGN_ID}';" -sN)
echo -e "\n${BLUE}Orders in Database: ${TOTAL_ORDERS}${NC}"

echo -e "\n${GREEN}✓ Aggressive performance test completed!${NC}"
