#!/bin/bash
# =============================================================================
# ⛔ STOP! READ THIS BEFORE RUNNING OR EDITING ⛔
# =============================================================================
#
# THIS SCRIPT IS FOR VARIANT Y (BASELINE) ONLY.
#
# DO NOT EDIT this script to test your new variant.
# DO NOT RUN this script to test your new variant.
#
# PURPOSE:
#   1. Validates the shared environment (Docker, Network, DB).
#   2. Validates Variant Y (the "Control Group") is healthy.
#
# IF YOU ARE CREATING A NEW VARIANT (e.g., Variant B):
#   1. Create your own script: variant-b/verify_variant_b.sh
#   2. Copy the template: scripts/verification/template_verify_variant.sh
#   3. Customize YOUR script, leave this one alone.
#
# =============================================================================

# =============================================================================
# SACRED VERIFICATION - Variant Y Golden Standard Verification
# =============================================================================
# This is the GOLDEN COMMAND for verifying Variant Y integrity.
# Run this whenever you need to ensure Variant Y is working perfectly.
#
# Usage: bash SACRED_VERIFICATION.sh [DURATION]
#
# Arguments:
#   DURATION - Optional base test duration in seconds (default: 10)
#
# This script follows Policy 4: Mandatory Functionality Verification:
#   1. Removes any Variant X conflicts
#   2. Ensures all services are running
#   3. Runs health checks
#   4. Runs unit tests
#   5-9. Runs adaptive plateau detection for all service/endpoint combinations:
#      Step 1: Individual service health benchmarks (direct)
#      Step 2: Nginx health benchmark
#      Step 3: Individual service ORDER benchmarks (direct) - CRITICAL!
#      Step 4: Nginx ORDER benchmark (round-robin)
#
# TESTING METHODOLOGY:
#   - NO QUICK MODE - Always finds true plateau or peak
#   - Adaptive testing: dynamically adjusts threads/concurrency
#   - Growth analysis: >5% = significant, 2-5% = moderate, <2% = marginal
#   - Plateau detection: <2% variance across 3 consecutive tests
#   - Error policy: Stop immediately on ANY 503 error
#   - Results: All data written to CSV, pivot summary generated at end
#
# Exit codes:
#   0 = SACRED VERIFICATION PASSED
#   1 = SACRED VERIFICATION FAILED
# =============================================================================

set -e

# Hardcoded Sacred Configuration
SACRED_ROOT="/home/syracuse/flashsale"
EXPECTED_VARIANT="variant_y"

# Strict Directory Enforcement
# Usage: bash SACRED_VERIFICATION.sh [DIRECTORY] [DURATION]
PASSED_DIR="${1:-$SACRED_ROOT}"
DURATION="${2:-10}"

if [ "$PASSED_DIR" != "$SACRED_ROOT" ]; then
    echo -e "\033[0;31mERROR: SACRED VERIFICATION is locked to Variant Y baseline.\033[0m"
    echo -e "\033[0;31mTarget directory MUST be: $SACRED_ROOT\033[0m"
    echo -e "\033[0;31mReceived: $PASSED_DIR\033[0m"
    exit 1
fi

# Ensure we are actually IN that directory
cd "$SACRED_ROOT"

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="${SACRED_ROOT}/benchmark_results"
CSV_FILE="${RESULTS_DIR}/variant_Y_raw_${TIMESTAMP}.csv"

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
echo -e "${BLUE}Testing Mode: FULL (Adaptive Plateau Detection)${NC}"
echo -e "${BLUE}Base Duration: ${DURATION}s${NC}"
echo -e "${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

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
VARIANT_X_CONTAINERS=$(docker ps -a --format "{{.Names}}" | grep -E "variant-x|variantx" || true)
if [ -n "$VARIANT_X_CONTAINERS" ]; then
    echo -e "${RED}⚠ Variant X containers detected, stopping and removing...${NC}"
    echo "$VARIANT_X_CONTAINERS" | xargs -r docker stop
    echo "$VARIANT_X_CONTAINERS" | xargs -r docker rm
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

CONTAINERS=("flash-mariadb-y" "flash-python-y" "flash-java-y" "flash-csharp-y" "flash-nginx-y")
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

    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${GREEN}✓ All services already running${NC}"
fi

# Verify all containers are up
echo -e "\n${BLUE}Container Status:${NC}"
for container in "${CONTAINERS[@]}"; do
    STATUS=$(docker ps --filter "name=^${container}$" --format "{{.Status}}" 2>/dev/null || echo "NOT RUNNING")
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
if docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1; then
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

TEST_OUTPUT=$(docker exec flash-python-y python -m pytest 2>&1)
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
# Step 5: Prepare Test Data and Initialize CSV
# =============================================================================
echo -e "\n${YELLOW}[Step 5/9] Preparing test data and CSV output...${NC}"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Initialize CSV file with header
cat > "$CSV_FILE" << 'EOF'
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
EOF

echo -e "${GREEN}✓ CSV initialized: ${CSV_FILE}${NC}"

# Ensure test data exists
if [ ! -f /tmp/stress_test_sku_ids.txt ]; then
    echo -e "${BLUE}Generating test data (500 SPUs, 2500 SKUs)...${NC}"
    docker exec flash-python-y python /app/setup_test_data.py 500 5 10000 > /dev/null 2>&1
    docker cp flash-python-y:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt 2>/dev/null || true
    echo -e "${GREEN}✓ Test data generated${NC}"
else
    echo -e "${GREEN}✓ Test data already exists${NC}"
fi

# Copy benchmark script to /tmp
if [ ! -f /tmp/order_benchmark.lua ]; then
    if [ -f python-service/wrk_order_script.lua ]; then
        cp python-service/wrk_order_script.lua /tmp/order_benchmark.lua
        echo -e "${GREEN}✓ Order benchmark script copied${NC}"
    else
        echo -e "${RED}✗ wrk_order_script.lua not found${NC}"
        echo -e "${RED}SACRED VERIFICATION FAILED: Missing benchmark script${NC}"
        exit 1
    fi
fi

# Source plateau detection library
source ./lib/plateau_detector.sh

# =============================================================================
# Policy 4 - Step 1: Individual Service Health Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}[Step 6/9] Policy 4 Step 1 - Health Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}Using adaptive plateau detection to find optimal performance${NC}\n"

run_adaptive_test "variant_y" "python" "8000" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_y" "java" "8081" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_y" "csharp" "8082" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Policy 4 - Step 2: Nginx Health Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 7/9] Policy 4 Step 2 - Nginx Health Benchmark${NC}"
echo -e "${BLUE}Testing Nginx round-robin load balancing${NC}\n"

run_adaptive_test "variant_y" "nginx" "8443" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Policy 4 - Step 3: Individual Service Order Benchmarks (CRITICAL!)
# =============================================================================
echo -e "\n${YELLOW}[Step 8/9] Policy 4 Step 3 - Order Processing Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}*** CRITICAL: This tests CORE flash sale functionality! ***${NC}\n"

run_adaptive_test "variant_y" "python" "8000" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_y" "java" "8081" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_y" "csharp" "8082" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Policy 4 - Step 4: Nginx Order Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 9/9] Policy 4 Step 4 - Nginx Order Benchmark (Round-Robin)${NC}"
echo -e "${BLUE}Testing Nginx order processing with load balancing${NC}\n"

run_adaptive_test "variant_y" "nginx" "8443" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Generate Pivot Summary
# =============================================================================
echo -e "\n${YELLOW}Generating pivot summary from CSV data...${NC}"

if [ -f "./generate_pivot_summary.py" ]; then
    python3 ./generate_pivot_summary.py "$CSV_FILE"
    echo -e "${GREEN}✓ Pivot summary generated${NC}"
else
    echo -e "${YELLOW}⚠ generate_pivot_summary.py not found, skipping pivot generation${NC}"
    echo -e "${BLUE}Raw CSV data available at: ${CSV_FILE}${NC}"
fi

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
echo "  • Performance analysis and optimization"
echo "  • Production testing"
echo ""
echo -e "${BLUE}Test Results:${NC}"
echo "  CSV Raw Data:    ${CSV_FILE}"
echo "  Pivot Summary:   ${RESULTS_DIR}/summary_${TIMESTAMP}.md"
echo ""
echo -e "${BLUE}DataGrip Connection (Always Available):${NC}"
echo "  Host: localhost"
echo "  Port: 3307"
echo "  Database: orange315"
echo "  User: syracuse"
echo "  Password: Orange_315_Forever!"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  Status check:    bash check_variant_y.sh"
echo "  View CSV:        cat ${CSV_FILE} | column -t -s,"
echo "  Unit tests:      docker exec flash-python-y python -m pytest"

exit 0
