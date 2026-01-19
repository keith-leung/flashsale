#!/bin/bash
# Variant Z - Initialize Test Data and Run Proper Benchmarks
# This script ensures valid SKUs exist and tokens are allocated before benchmarking

set -e

echo "=========================================="
echo "Variant Z - Initialize and Benchmark"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Check if services are running
echo -e "\n${YELLOW}[1/6] Checking services...${NC}"
if ! docker ps | grep -q "flash-mariadb-z"; then
    echo -e "${RED}✗ MariaDB not running${NC}"
    exit 1
fi
if ! docker ps | grep -q "flash-redis-z"; then
    echo -e "${RED}✗ Redis not running${NC}"
    exit 1
fi
if ! docker ps | grep -q "flash-python-z"; then
    echo -e "${RED}✗ Python service not running${NC}"
    exit 1
fi
if ! docker ps | grep -q "flash-csharp-z"; then
    echo -e "${RED}✗ C# service not running${NC}"
    exit 1
fi
if ! docker ps | grep -q "flash-java-z"; then
    echo -e "${RED}✗ Java service not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ All services running${NC}"

# Step 2: Initialize database
echo -e "\n${YELLOW}[2/6] Initializing database...${NC}"
docker exec flash-python-z python /app/init_db.py 2>&1 | grep -v "already exists" || true
echo -e "${GREEN}✓ Database initialized${NC}"

# Step 3: Create test campaign and SKU
echo -e "\n${YELLOW}[3/6] Creating test campaign and SKU...${NC}"
docker exec flash-python-z python /app/setup_test_data.py 1 1 10000 2>&1 | tail -5
echo -e "${GREEN}✓ Test data created${NC}"

# Step 4: Get valid SKU ID from database
echo -e "\n${YELLOW}[4/6] Getting valid SKU ID...${NC}"
SKU_ID=$(docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -se "SELECT id FROM skus LIMIT 1" 2>/dev/null | tail -1)
CAMPAIGN_ID=$(docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -se "SELECT id FROM flash_sale_campaigns LIMIT 1" 2>/dev/null | tail -1)

if [ -z "$SKU_ID" ]; then
    echo -e "${RED}✗ No SKU found in database${NC}"
    exit 1
fi

echo -e "${GREEN}✓ SKU ID: $SKU_ID${NC}"
echo -e "${GREEN}✓ Campaign ID: $CAMPAIGN_ID${NC}"

# Step 5: Allocate tokens for campaign
echo -e "\n${YELLOW}[5/6] Allocating campaign tokens...${NC}"
docker exec flash-python-z python /app/allocate_all_campaign_tokens.py 2>&1 | tail -10

# Verify tokens allocated
TOKEN_COUNT=$(docker exec flash-redis-z redis-cli ZCARD "campaign:${CAMPAIGN_ID}:tokens" 2>/dev/null || echo "0")
if [ "$TOKEN_COUNT" -lt 100 ]; then
    echo -e "${RED}✗ Token allocation failed (only $TOKEN_COUNT tokens)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Tokens allocated: $TOKEN_COUNT${NC}"

# Step 6: Create updated wrk script with valid SKU
echo -e "\n${YELLOW}[6/6] Creating benchmark script...${NC}"
cat > /tmp/wrk_order_script_valid.lua << EOF
-- wrk Lua script for testing flash sale orders
local campaign_id = "$CAMPAIGN_ID"
local sku_id = "$SKU_ID"
local counter = 0

request = function()
    counter = counter + 1
    local email = string.format("test%d@example.com", counter)
    local body = string.format([[{
        "customer_email": "%s",
        "customer_name": "Test User %d",
        "line_items": [{
            "sku_id": "%s",
            "quantity": 1
        }]
    }]], email, counter, sku_id)
    local headers = {
        ["Content-Type"] = "application/json",
        ["Accept"] = "application/json"
    }
    return wrk.format("POST", nil, headers, body)
end

local success_count = 0
local error_count = 0
local sold_out_count = 0

response = function(status, headers, body)
    if status == 201 then
        success_count = success_count + 1
    elseif status == 400 and body:find("sold out") then
        sold_out_count = sold_out_count + 1
    else
        error_count = error_count + 1
    end
end

done = function(summary, latency, requests)
    io.write("\n")
    io.write("========================================\n")
    io.write("Request Statistics:\n")
    io.write(string.format("  Total Requests:  %d\n", summary.requests))
    io.write(string.format("  Success (201):   %d\n", success_count))
    io.write(string.format("  Sold Out:        %d\n", sold_out_count))
    io.write(string.format("  Errors:          %d\n", error_count))
    io.write(string.format("  Error Rate:      %.2f%%\n", (error_count / summary.requests) * 100))
    io.write("========================================\n")
end
EOF

echo -e "${GREEN}✓ Benchmark script created${NC}"

# Test single order to verify setup
echo -e "\n${YELLOW}Testing single order...${NC}"
TEST_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:30017/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d "{\"customer_name\":\"Test\",\"customer_email\":\"test@example.com\",\"line_items\":[{\"sku_id\":\"$SKU_ID\",\"quantity\":1}]}")

HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -1)
if [ "$HTTP_CODE" != "201" ]; then
    echo -e "${RED}✗ Single order test failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $TEST_RESPONSE"
    exit 1
fi
echo -e "${GREEN}✓ Single order test passed${NC}"

echo -e "\n${GREEN}=========================================="
echo "Initialization Complete!"
echo "=========================================="
echo -e "SKU ID: $SKU_ID"
echo -e "Campaign ID: $CAMPAIGN_ID"
echo -e "Tokens: $TOKEN_COUNT"
echo -e "\nRun benchmarks with:"
echo -e "  wrk -t 4 -c 50 -d 30s -s /tmp/wrk_order_script_valid.lua http://localhost:30017/api/v1/orders/"
echo -e "  wrk -t 4 -c 50 -d 30s -s /tmp/wrk_order_script_valid.lua http://localhost:30018/api/v1/orders"
echo -e "  wrk -t 4 -c 50 -d 30s -s /tmp/wrk_order_script_valid.lua http://localhost:8019/api/v1/orders"
echo -e "=========================================="