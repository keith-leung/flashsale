#!/bin/bash
# Fast Performance Test - Quick validation
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

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════════"
echo "         FAST Performance Test - Quick Validation"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo "Target: 5,000 orders in 1-2 minutes"
echo "Concurrency: 100"
echo ""

# Test single order
echo -e "${YELLOW}[Pre-check] Testing single order...${NC}"
RESPONSE=$(curl -s -X POST $URL \
    -H "Content-Type: application/json" \
    -d "{
        \"customer_email\": \"precheck@example.com\",
        \"customer_name\": \"Pre Check\",
        \"line_items\": [{\"sku_id\": \"${SKU_ID}\", \"quantity\": 1}],
        \"flash_sale_campaign_id\": \"${CAMPAIGN_ID}\",
        \"currency\": \"USD\"
    }")

if echo "$RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✓ Order creation working${NC}"
else
    echo -e "${RED}✗ Order creation failed${NC}"
    echo "$RESPONSE"
    exit 1
fi

# Fast test with high concurrency
echo -e "\n${BOLD}${YELLOW}Running fast test: 5,000 orders with 100 concurrent connections${NC}\n"

START_TIME=$(date +%s)
SUCCESS_COUNT=0
FAIL_COUNT=0

# Create orders in batches
TOTAL_ORDERS=5000
CONCURRENCY=100
BATCH_SIZE=$((CONCURRENCY * 5))

for batch_start in $(seq 1 $BATCH_SIZE $TOTAL_ORDERS); do
    batch_end=$((batch_start + BATCH_SIZE - 1))
    if [ $batch_end -gt $TOTAL_ORDERS ]; then
        batch_end=$TOTAL_ORDERS
    fi

    # Launch batch in parallel
    for i in $(seq $batch_start $batch_end); do
        {
            RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $URL \
                -H "Content-Type: application/json" \
                -d "{
                    \"customer_email\": \"fast${i}@test.com\",
                    \"customer_name\": \"Fast Test ${i}\",
                    \"line_items\": [{\"sku_id\": \"${SKU_ID}\", \"quantity\": 1}],
                    \"flash_sale_campaign_id\": \"${CAMPAIGN_ID}\",
                    \"currency\": \"USD\"
                }" 2>&1)

            HTTP_CODE=$(echo "$RESPONSE" | tail -1)
            if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
                echo "SUCCESS"
            else
                echo "FAIL"
            fi
        } &

        # Limit concurrent connections
        if [ $((i % CONCURRENCY)) -eq 0 ]; then
            wait
        fi
    done

    wait

    # Progress update
    COMPLETED=$batch_end
    ELAPSED=$(($(date +%s) - START_TIME))
    THROUGHPUT=$(awk "BEGIN {printf \"%.1f\", $COMPLETED / $ELAPSED}")
    echo -ne "\rProgress: ${COMPLETED}/${TOTAL_ORDERS} orders | Throughput: ${THROUGHPUT} req/s"
done

echo ""

# Count results
SUCCESS_COUNT=$(cat /tmp/fast_test_results_* 2>/dev/null | grep -c "SUCCESS" || echo 0)
FAIL_COUNT=$(cat /tmp/fast_test_results_* 2>/dev/null | grep -c "FAIL" || echo 0)
rm -f /tmp/fast_test_results_* 2>/dev/null

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
THROUGHPUT=$(awk "BEGIN {printf \"%.2f\", $TOTAL_ORDERS / $DURATION}")

echo -e "\n${GREEN}✓ Fast test completed${NC}"
echo -e "${BLUE}Duration: ${DURATION}s${NC}"
echo -e "${BLUE}Throughput: ${BOLD}${THROUGHPUT} req/s${NC}"
echo -e "${BLUE}Total Orders: ${TOTAL_ORDERS}${NC}"

# Verify in database
DB_COUNT=$(docker exec flash-mariadb-a mysql -uroot -proot orange315 -e "SELECT COUNT(*) FROM orders WHERE flash_sale_campaign_id = '${CAMPAIGN_ID}' AND customer_email LIKE 'fast%';" -sN 2>/dev/null || echo 0)
echo -e "${BLUE}Orders in Database: ${DB_COUNT}${NC}"

if [ "$DB_COUNT" -ge 4900 ]; then
    echo -e "\n${GREEN}✓ Fast test PASSED - System ready for aggressive test${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠ Only ${DB_COUNT} orders created - check system${NC}"
    exit 1
fi
