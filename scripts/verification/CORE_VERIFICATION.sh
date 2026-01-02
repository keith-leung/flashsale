#!/bin/bash
# =============================================================================
# CORE VERIFICATION - Essential Functionality Check (No Benchmarks)
# =============================================================================
# This verifies core functionality without requiring wrk benchmarking tool
#
# Usage: bash CORE_VERIFICATION.sh
#
# Exit codes:
#   0 = CORE VERIFICATION PASSED
#   1 = CORE VERIFICATION FAILED
# =============================================================================

set -e

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "                   CORE VERIFICATION"
echo "           Variant Y Essential Functionality Check"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# =============================================================================
# Step 1: Check Variant X Conflicts
# =============================================================================
echo -e "${YELLOW}[Step 1/6] Checking for Variant X conflicts...${NC}"

CONFLICTS_FOUND=false

if [ -f "docker-compose-variant-x.yml" ] || [ -f "docker-compose-variant-x-simple.yml" ] || [ -f "docker-compose-simple.yml" ]; then
    echo -e "${RED}⚠ Variant X conflicts detected${NC}"
    CONFLICTS_FOUND=true
    mkdir -p archived-variant-x
    [ -f "docker-compose-variant-x.yml" ] && mv docker-compose-variant-x.yml archived-variant-x/
    [ -f "docker-compose-variant-x-simple.yml" ] && mv docker-compose-variant-x-simple.yml archived-variant-x/
    [ -f "docker-compose-simple.yml" ] && mv docker-compose-simple.yml archived-variant-x/
fi

VARIANT_X_CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep -E "variant-x|variantx" || true)
if [ -n "$VARIANT_X_CONTAINERS" ]; then
    echo -e "${RED}⚠ Variant X containers detected, stopping and removing...${NC}"
    echo "$VARIANT_X_CONTAINERS" | xargs -r docker stop
    echo "$VARIANT_X_CONTAINERS" | xargs -r docker rm
    CONFLICTS_FOUND=true
fi

if [ "$CONFLICTS_FOUND" = false ]; then
    echo -e "${GREEN}✓ No Variant X conflicts found${NC}"
fi

# =============================================================================
# Step 2: Ensure All Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[Step 2/6] Ensuring all Variant Y services are running...${NC}"

CONTAINERS=("flash-mariadb-y" "flash-redis-y" "flash-python-y" "flash-java-y" "flash-csharp-y" "flash-nginx-y")
NEED_START=false

for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        NEED_START=true
        break
    fi
done

if [ "$NEED_START" = true ]; then
    echo -e "${YELLOW}Starting Variant Y services...${NC}"
    docker compose up -d
    echo -e "${YELLOW}Waiting 30s for services to initialize...${NC}"
    sleep 30
fi

echo -e "\n${BLUE}Container Status:${NC}"
for container in "${CONTAINERS[@]}"; do
    STATUS=$(docker ps --filter "name=^${container}$" --format "{{.Status}}" 2>/dev/null || echo "NOT RUNNING")
    if [[ "$STATUS" == "Up"* ]]; then
        echo -e "${GREEN}  ✓ ${container}: ${STATUS}${NC}"
    else
        echo -e "${RED}  ✗ ${container}: ${STATUS}${NC}"
        echo -e "${RED}CORE VERIFICATION FAILED: ${container} not running${NC}"
        exit 1
    fi
done

# =============================================================================
# Step 3: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 3/6] Running health checks...${NC}"

for i in {1..20}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1 && \
       curl -sf http://localhost:8081/health > /dev/null 2>&1 && \
       curl -sf http://localhost:8082/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ All HTTP services ready${NC}"
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${RED}✗ Services not responding after 60s${NC}"
        exit 1
    fi
    echo "  Waiting for services... ($i/20)"
    sleep 3
done

curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo -e "${GREEN}✓ Python health OK${NC}" || { echo -e "${RED}✗ Python health FAILED${NC}"; exit 1; }
curl -sf http://localhost:8081/health > /dev/null 2>&1 && echo -e "${GREEN}✓ Java health OK${NC}" || { echo -e "${RED}✗ Java health FAILED${NC}"; exit 1; }
curl -sf http://localhost:8082/health > /dev/null 2>&1 && echo -e "${GREEN}✓ C# health OK${NC}" || { echo -e "${RED}✗ C# health FAILED${NC}"; exit 1; }

docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1 && \
    echo -e "${GREEN}✓ MariaDB connection OK${NC}" || { echo -e "${RED}✗ MariaDB connection FAILED${NC}"; exit 1; }

# =============================================================================
# Step 4: Unit Tests
# =============================================================================
echo -e "\n${YELLOW}[Step 4/6] Running unit tests...${NC}"

TEST_OUTPUT=$(docker exec flash-python-y python -m pytest 2>&1)
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' | tail -1)
    echo -e "${GREEN}✓ Unit tests PASSED: ${PASSED} tests${NC}"
else
    echo -e "${RED}✗ Unit tests FAILED${NC}"
    echo "$TEST_OUTPUT"
    exit 1
fi

# =============================================================================
# Step 5: Database Schema Verification
# =============================================================================
echo -e "\n${YELLOW}[Step 5/6] Verifying database schema...${NC}"

# Check flash_sale_campaigns table exists with correct structure
CAMPAIGN_TABLE=$(docker exec flash-mariadb-y mysql -uroot -proot orange315 -e "SHOW TABLES LIKE 'flash_sale_campaigns';" 2>/dev/null | grep flash_sale_campaigns || echo "")

if [ -z "$CAMPAIGN_TABLE" ]; then
    echo -e "${RED}✗ flash_sale_campaigns table not found${NC}"
    exit 1
fi

# Verify spu_id column exists (not sku_id)
SPU_COL=$(docker exec flash-mariadb-y mysql -uroot -proot orange315 -e "SHOW COLUMNS FROM flash_sale_campaigns LIKE 'spu_id';" 2>/dev/null | grep spu_id || echo "")

if [ -z "$SPU_COL" ]; then
    echo -e "${RED}✗ flash_sale_campaigns.spu_id column not found (should be SPU-level, not SKU-level)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database schema verified (flash_sale_campaigns is SPU-level)${NC}"

# =============================================================================
# Step 6: Functional API Tests
# =============================================================================
echo -e "\n${YELLOW}[Step 6/6] Running functional API tests...${NC}"

# Test 1: Create test order
echo -e "${BLUE}Testing order creation API...${NC}"
ORDER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test Customer",
    "line_items": [
      {
        "sku_id": "650e8400-e29b-41d4-a716-446655440001",
        "quantity": 1
      }
    ],
    "currency": "USD"
  }' 2>&1)

if echo "$ORDER_RESPONSE" | grep -q '"status":201'; then
    echo -e "${GREEN}✓ Order creation API working${NC}"
else
    echo -e "${RED}✗ Order creation API failed${NC}"
    echo "$ORDER_RESPONSE"
    exit 1
fi

# Test 2: List orders
echo -e "${BLUE}Testing order list API...${NC}"
LIST_RESPONSE=$(curl -s http://localhost:8000/api/v1/orders 2>&1)

if echo "$LIST_RESPONSE" | grep -q '"data"'; then
    echo -e "${GREEN}✓ Order list API working${NC}"
else
    echo -e "${RED}✗ Order list API failed${NC}"
    exit 1
fi

# =============================================================================
# CORE VERIFICATION PASSED
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "              ✓ CORE VERIFICATION PASSED ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Variant Y core functionality is working:${NC}"
echo "  ✓ All containers running"
echo "  ✓ Health checks passing"
echo "  ✓ Unit tests passing (${PASSED} tests)"
echo "  ✓ Database schema correct (SPU-level campaigns)"
echo "  ✓ API endpoints functional"
echo ""
echo -e "${BLUE}DataGrip Connection:${NC}"
echo "  Host: localhost"
echo "  Port: 3307"
echo "  Database: orange315"
echo "  User: syracuse"
echo "  Password: Orange_315_Forever!"
echo ""
echo -e "${YELLOW}Note: Full SACRED_VERIFICATION.sh requires 'wrk' for benchmarks${NC}"
echo -e "${YELLOW}To install wrk: sudo apt-get install wrk${NC}"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  Status check:  bash check_variant_y.sh"
echo "  Unit tests:    docker exec flash-python-y python -m pytest"
echo "  View logs:     docker logs flash-python-y"

exit 0
