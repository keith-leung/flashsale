#!/bin/bash
# =============================================================================
# SACRED VERIFICATION - Variant Y Golden Standard Verification
# =============================================================================
# This is the GOLDEN COMMAND for verifying Variant Y integrity.
# Run this whenever you need to ensure Variant Y is working perfectly.
#
# Usage: bash SACRED_VERIFICATION.sh
#
# This script follows Policy 4: Mandatory Functionality Verification:
#   1. Removes any Variant X conflicts
#   2. Ensures all services are running
#   3. Runs health checks
#   4. Runs unit tests
#   5-9. Runs Policy 4 complete 4-step benchmark (5s per test):
#      Step 1: Individual service health benchmarks (direct)
#      Step 2: Nginx health benchmark
#      Step 3: Individual service ORDER benchmarks (direct) - CRITICAL!
#      Step 4: Nginx ORDER benchmark (round-robin)
#
# Exit codes:
#   0 = SACRED VERIFICATION PASSED
#   1 = SACRED VERIFICATION FAILED
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
echo "                   SACRED VERIFICATION"
echo "           Variant Y Golden Standard Verification"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# =============================================================================
# Step 1: Remove Variant X Conflicts
# =============================================================================
echo -e "${YELLOW}[Step 1/9] Checking for Variant X conflicts...${NC}"

CONFLICTS_FOUND=false

if [ -f "docker-compose-variant-x.yml" ] || [ -f "docker-compose-variant-x-simple.yml" ] || [ -f "docker-compose-simple.yml" ]; then
    echo -e "${RED}⚠ Variant X conflicts detected${NC}"
    CONFLICTS_FOUND=true

    mkdir -p archived-variant-x

    if [ -f "docker-compose-variant-x.yml" ]; then
        mv docker-compose-variant-x.yml archived-variant-x/
        echo -e "${GREEN}✓ Archived docker-compose-variant-x.yml${NC}"
    fi

    if [ -f "docker-compose-variant-x-simple.yml" ]; then
        mv docker-compose-variant-x-simple.yml archived-variant-x/
        echo -e "${GREEN}✓ Archived docker-compose-variant-x-simple.yml${NC}"
    fi

    if [ -f "docker-compose-simple.yml" ]; then
        mv docker-compose-simple.yml archived-variant-x/
        echo -e "${GREEN}✓ Archived docker-compose-simple.yml${NC}"
    fi
fi

# Check for conflicting containers
VARIANT_X_CONTAINERS=$(podman ps -a --format "{{.Names}}" | grep -E "variant-x|variantx" || true)
if [ -n "$VARIANT_X_CONTAINERS" ]; then
    echo -e "${RED}⚠ Variant X containers detected, stopping and removing...${NC}"
    echo "$VARIANT_X_CONTAINERS" | xargs -r podman stop
    echo "$VARIANT_X_CONTAINERS" | xargs -r podman rm
    echo -e "${GREEN}✓ Removed Variant X containers${NC}"
    CONFLICTS_FOUND=true
fi

if [ "$CONFLICTS_FOUND" = false ]; then
    echo -e "${GREEN}✓ No Variant X conflicts found${NC}"
fi

# =============================================================================
# Step 2: Ensure All Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[Step 2/9] Ensuring all Variant Y services are running...${NC}"

CONTAINERS=("flash-mariadb" "flash-redis" "flash-python" "flash-java" "flash-csharp" "flash-nginx")
NEED_START=false

for container in "${CONTAINERS[@]}"; do
    if ! podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
        NEED_START=true
        break
    fi
done

if [ "$NEED_START" = true ]; then
    echo -e "${YELLOW}Starting Variant Y services...${NC}"
    podman-compose up -d

    echo -e "${YELLOW}Waiting 30s for services to initialize...${NC}"
    sleep 30

    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${GREEN}✓ All services already running${NC}"
fi

# Verify all containers are up
echo -e "\n${BLUE}Container Status:${NC}"
for container in "${CONTAINERS[@]}"; do
    STATUS=$(podman ps --filter "name=^${container}$" --format "{{.Status}}" 2>/dev/null || echo "NOT RUNNING")
    if [[ "$STATUS" == "Up"* ]]; then
        echo -e "${GREEN}  ✓ ${container}: ${STATUS}${NC}"
    else
        echo -e "${RED}  ✗ ${container}: ${STATUS}${NC}"
        echo -e "${RED}SACRED VERIFICATION FAILED: ${container} not running${NC}"
        exit 1
    fi
done

# =============================================================================
# Step 3: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 3/9] Running health checks...${NC}"

# Wait for services to be ready
echo -e "${BLUE}Waiting for HTTP services to respond...${NC}"
for i in {1..20}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1 && \
       curl -sf http://localhost:8081/health > /dev/null 2>&1 && \
       curl -sf http://localhost:8082/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ All HTTP services ready${NC}"
        break
    fi

    if [ $i -eq 20 ]; then
        echo -e "${RED}✗ Services not responding after 60s${NC}"
        echo -e "${RED}SACRED VERIFICATION FAILED: Health checks timed out${NC}"
        exit 1
    fi

    echo "  Waiting for services... ($i/20)"
    sleep 3
done

# Test each service
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Python health OK${NC}"
else
    echo -e "${RED}✗ Python health FAILED${NC}"
    echo -e "${RED}SACRED VERIFICATION FAILED: Python health check${NC}"
    exit 1
fi

if curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Java health OK${NC}"
else
    echo -e "${RED}✗ Java health FAILED${NC}"
    echo -e "${RED}SACRED VERIFICATION FAILED: Java health check${NC}"
    exit 1
fi

if curl -sf http://localhost:8082/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ C# health OK${NC}"
else
    echo -e "${RED}✗ C# health FAILED${NC}"
    echo -e "${RED}SACRED VERIFICATION FAILED: C# health check${NC}"
    exit 1
fi

# Test database
if podman exec flash-mariadb mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MariaDB connection OK${NC}"
else
    echo -e "${RED}✗ MariaDB connection FAILED${NC}"
    echo -e "${RED}SACRED VERIFICATION FAILED: Database connection${NC}"
    exit 1
fi

# =============================================================================
# Step 4: Unit Tests
# =============================================================================
echo -e "\n${YELLOW}[Step 4/9] Running unit tests...${NC}"

TEST_OUTPUT=$(podman exec flash-python python -m pytest 2>&1)
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    PASSED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= passed)' | tail -1)
    echo -e "${GREEN}✓ Unit tests PASSED: ${PASSED} tests${NC}"
else
    echo -e "${RED}✗ Unit tests FAILED${NC}"
    echo "$TEST_OUTPUT"
    echo -e "${RED}SACRED VERIFICATION FAILED: Unit tests${NC}"
    exit 1
fi

# =============================================================================
# Step 5: Prepare Test Data
# =============================================================================
echo -e "\n${YELLOW}[Step 5/9] Preparing test data...${NC}"

# Ensure test data exists
if [ ! -f /tmp/stress_test_sku_ids.txt ]; then
    echo -e "${BLUE}Generating test data (500 SPUs, 2500 SKUs)...${NC}"
    podman exec flash-python python /app/setup_test_data.py 500 5 10000 > /dev/null 2>&1
    podman cp flash-python:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt 2>/dev/null || true
    echo -e "${GREEN}✓ Test data generated${NC}"
else
    echo -e "${GREEN}✓ Test data already exists${NC}"
fi

# Copy benchmark script to /tmp
if [ ! -f /tmp/order_benchmark.lua ]; then
    if [ -f python-service/wrk_order_script.lua ]; then
        cp python-service/wrk_order_script.lua /tmp/order_benchmark.lua
    else
        echo -e "${RED}✗ wrk_order_script.lua not found${NC}"
        echo -e "${RED}SACRED VERIFICATION FAILED: Missing benchmark script${NC}"
        exit 1
    fi
fi

# Helper function to run wrk and validate results
run_wrk_test() {
    local test_name="$1"
    local wrk_command="$2"
    local expect_orders="$3"  # "true" if testing orders (check for errors)

    echo -e "${BLUE}${test_name}${NC}"
    echo -e "${BLUE}Command: ${wrk_command}${NC}"

    # Run wrk and capture output
    local output=$(eval "$wrk_command" 2>&1)

    # Display full output
    echo "$output"

    # Check for Non-2xx responses (indicates all requests failed)
    if echo "$output" | grep -q "Non-2xx or 3xx responses:"; then
        local non_2xx=$(echo "$output" | grep "Non-2xx or 3xx responses:" | awk '{print $NF}')
        local total_req=$(echo "$output" | grep "requests in" | awk '{print $1}')

        if [ "$non_2xx" == "$total_req" ]; then
            echo -e "${RED}✗ ALL REQUESTS FAILED (100% error rate)${NC}"
            echo -e "${RED}SACRED VERIFICATION FAILED: ${test_name}${NC}"
            exit 1
        fi
    fi

    # Extract and validate req/s
    local req_sec=$(echo "$output" | grep "Requests/sec:" | awk '{print $2}')

    if [ -z "$req_sec" ] || [ "$req_sec" == "0.00" ]; then
        echo -e "${RED}✗ No throughput measured${NC}"
        echo -e "${RED}SACRED VERIFICATION FAILED: ${test_name}${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ ${test_name}: ${req_sec} req/s${NC}\n"
}

# =============================================================================
# Policy 4 - Step 1: Individual Service Health Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}[Step 6/9] Policy 4 Step 1 - Health Benchmarks (Direct Access)${NC}"

run_wrk_test "Python Health" "wrk -t12 -c100 -d5s http://localhost:8000/health" "false"
run_wrk_test "Java Health" "wrk -t12 -c200 -d5s http://localhost:8081/health" "false"
run_wrk_test "C# Health" "wrk -t12 -c600 -d5s http://localhost:8082/health" "false"

# =============================================================================
# Policy 4 - Step 2: Nginx Health Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 7/9] Policy 4 Step 2 - Nginx Health Benchmark${NC}"

run_wrk_test "Nginx Health" "wrk -t12 -c25 -d5s https://localhost:8443/health" "false"

# =============================================================================
# Policy 4 - Step 3: Individual Service Order Benchmarks (CRITICAL!)
# =============================================================================
echo -e "\n${YELLOW}[Step 8/9] Policy 4 Step 3 - Order Processing Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}*** CRITICAL: This tests CORE flash sale functionality! ***${NC}\n"

run_wrk_test "Python Orders" "wrk -t12 -c50 -d5s -s /tmp/order_benchmark.lua http://localhost:8000/api/v1/orders" "true"
run_wrk_test "Java Orders" "wrk -t12 -c75 -d5s -s /tmp/order_benchmark.lua http://localhost:8081/api/v1/orders" "true"
run_wrk_test "C# Orders" "wrk -t12 -c25 -d5s -s /tmp/order_benchmark.lua http://localhost:8082/api/v1/orders" "true"

# =============================================================================
# Policy 4 - Step 4: Nginx Order Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 9/9] Policy 4 Step 4 - Nginx Order Benchmark (Round-Robin)${NC}"

run_wrk_test "Nginx Orders" "wrk -t4 -c50 -d5s -s /tmp/order_benchmark.lua https://localhost:8443/api/v1/orders" "true"

# =============================================================================
# SACRED VERIFICATION PASSED
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "              ✓ SACRED VERIFICATION PASSED ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Variant Y is GOLDEN and ready for:${NC}"
echo "  • Development and code changes"
echo "  • Full 4-step benchmarks: bash run_4step_benchmark.sh"
echo "  • Production testing"
echo ""
echo -e "${BLUE}DataGrip Connection (Always Available):${NC}"
echo "  Host: localhost"
echo "  Port: 3307"
echo "  Database: orange315"
echo "  User: syracuse"
echo "  Password: Orange_315_Forever!"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  Status check:  bash check_variant_y.sh"
echo "  Full benchmark: bash run_4step_benchmark.sh full"
echo "  Unit tests:    podman exec flash-python python -m pytest"

exit 0
