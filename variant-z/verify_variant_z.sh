#!/bin/bash
# =============================================================================
# VARIANT Z VERIFICATION SCRIPT
# Token Pre-Allocation Architecture
# =============================================================================
#
# This script follows the SACRED_VERIFICATION.sh pattern to verify Variant Z.
# It tests the complete Variant Z environment while ensuring no interference
# with Variant Y (the sacred baseline).
#
# Usage: bash verify_variant_z.sh [DURATION]
#
# Arguments:
#   DURATION - Optional base test duration in seconds (default: 10)
#
# This script follows Policy 4: Mandatory Functionality Verification:
#   1. Checks Variant Y is not disrupted
#   2. Ensures all Variant Z services are running
#   3. Runs health checks
#   4. Prepares test data (flash sale campaign with tokens)
#   5-8. Runs adaptive plateau detection for all service/endpoint combinations:
#      Step 1: Individual service health benchmarks (direct)
#      Step 2: Nginx health benchmark
#      Step 3: Individual service ORDER benchmarks (direct) - CRITICAL!
#      Step 4: Nginx ORDER benchmark (round-robin)
#
# Exit codes:
#   0 = VARIANT Z VERIFICATION PASSED
#   1 = VARIANT Z VERIFICATION FAILED
# =============================================================================

set -e

# Configuration
DURATION="${1:-10}"  # Default 10s, can be overridden
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/../benchmark_results"
CSV_FILE="${RESULTS_DIR}/variant_Z_raw_${TIMESTAMP}.csv"

# Variant Z ports
PYTHON_PORT="30017"
JAVA_PORT="8019"
CSHARP_PORT="30018"
NGINX_PORT="8448"
MARIADB_PORT="3315"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "                   VARIANT Z VERIFICATION"
echo "           Token Pre-Allocation Architecture"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "${BLUE}Testing Mode: FULL (Adaptive Plateau Detection)${NC}"
echo -e "${BLUE}Base Duration: ${DURATION}s${NC}"
echo -e "${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

# =============================================================================
# Step 1: Ensure Variant Y is Not Disrupted
# =============================================================================
echo -e "${YELLOW}[Step 1/9] Checking Variant Y baseline is protected...${NC}"

# Check if Variant Y is running (optional - just informational)
VARIANT_Y_CONTAINERS=("flash-mariadb-y" "flash-python-y" "flash-java-y" "flash-csharp-y" "flash-nginx-y")
VARIANT_Y_RUNNING=true

for container in "${VARIANT_Y_CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        VARIANT_Y_RUNNING=false
        break
    fi
done

if [ "$VARIANT_Y_RUNNING" = true ]; then
    echo -e "${GREEN}✓ Variant Y services are running (baseline protected)${NC}"
else
    echo -e "${YELLOW}⚠ Variant Y services not running (not required for Variant Z tests)${NC}"
fi

# =============================================================================
# Step 2: Ensure All Variant Z Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[Step 2/9] Ensuring all Variant Z services are running...${NC}"

CONTAINERS=("flash-mariadb-z" "flash-redis-z" "flash-python-z" "flash-java-z" "flash-csharp-z" "flash-nginx-z")
NEED_START=false

for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        NEED_START=true
        break
    fi
done

if [ "$NEED_START" = true ]; then
    echo -e "${YELLOW}Starting Variant Z services...${NC}"
    cd "$SCRIPT_DIR"
    docker compose up -d

    echo -e "${YELLOW}Waiting 60s for services to initialize...${NC}"
    sleep 60

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
        echo -e "${RED}VARIANT Z VERIFICATION FAILED: ${container} not running${NC}"
        exit 1
    fi
done

# =============================================================================
# Step 3: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 3/9] Running health checks...${NC}"

# Function to check service health with retries
check_health() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service} health OK (Port ${port})${NC}"
            return 0
        fi
        echo "  Waiting for ${service}... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}✗ ${service} health FAILED (Port ${port})${NC}"
    echo -e "${RED}VARIANT Z VERIFICATION FAILED: ${service} health check${NC}"
    exit 1
}

check_health "Python" "$PYTHON_PORT"
check_health "Java" "$JAVA_PORT"
check_health "C#" "$CSHARP_PORT"

# Test database
if docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MariaDB connection OK${NC}"
else
    echo -e "${RED}✗ MariaDB connection FAILED${NC}"
    echo -e "${RED}VARIANT Z VERIFICATION FAILED: Database connection${NC}"
    exit 1
fi

# Test Redis
if docker exec flash-redis-z redis-cli PING 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis connection OK${NC}"
else
    echo -e "${RED}✗ Redis connection FAILED${NC}"
    echo -e "${RED}VARIANT Z VERIFICATION FAILED: Redis connection${NC}"
    exit 1
fi

# =============================================================================
# Step 4: Prepare Test Data and Initialize CSV
# =============================================================================
echo -e "\n${YELLOW}[Step 4/9] Preparing test data and CSV output...${NC}"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Initialize CSV file with header
cat > "$CSV_FILE" << 'EOF'
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
EOF

echo -e "${GREEN}✓ CSV initialized: ${CSV_FILE}${NC}"

# Setup test data for Variant Z (flash sale with token pre-allocation)
echo -e "${BLUE}Setting up flash sale test data with token pre-allocation...${NC}"

# Run the setup script inside the Python container
docker exec flash-python-z python /app/setup_test_data.py 2>&1 || {
    echo -e "${RED}Failed to run setup_test_data.py${NC}"
    echo -e "${YELLOW}Attempting to initialize database first...${NC}"
    docker exec flash-python-z python /app/init_db.py 2>&1 || true
    docker exec flash-python-z python /app/setup_test_data.py 2>&1 || {
        echo -e "${RED}✗ Test data setup FAILED${NC}"
        exit 1
    }
}

# Copy SKU IDs file from container if it exists
docker cp flash-python-z:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt 2>/dev/null || {
    echo -e "${YELLOW}⚠ SKU IDs file not found, creating from database...${NC}"
    # Query database for SKU IDs and create the file
    docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! -N -e \
        "SELECT id FROM orange315.skus WHERE is_active = 1 LIMIT 100" > /tmp/stress_test_sku_ids.txt 2>/dev/null || {
        echo -e "${RED}✗ Could not get SKU IDs from database${NC}"
        exit 1
    }
}

# Verify we have SKU IDs
if [ -s /tmp/stress_test_sku_ids.txt ]; then
    SKU_COUNT=$(wc -l < /tmp/stress_test_sku_ids.txt)
    echo -e "${GREEN}✓ Test data ready: ${SKU_COUNT} SKUs available${NC}"
else
    echo -e "${RED}✗ No SKU IDs available for testing${NC}"
    exit 1
fi

# Copy wrk order script to /tmp
if [ -f "${SCRIPT_DIR}/wrk_order_script.lua" ]; then
    cp "${SCRIPT_DIR}/wrk_order_script.lua" /tmp/order_benchmark.lua
    echo -e "${GREEN}✓ Variant Z order benchmark script copied${NC}"
elif [ -f "${SCRIPT_DIR}/../python-service/wrk_order_script.lua" ]; then
    cp "${SCRIPT_DIR}/../python-service/wrk_order_script.lua" /tmp/order_benchmark.lua
    echo -e "${GREEN}✓ Variant Y order benchmark script copied (fallback)${NC}"
else
    echo -e "${RED}✗ No wrk order script found${NC}"
    exit 1
fi

# Source plateau detection library
source "${SCRIPT_DIR}/../lib/plateau_detector.sh"

# =============================================================================
# Step 5: Individual Service Health Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}[Step 5/9] Policy 4 Step 1 - Health Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}Using adaptive plateau detection to find optimal performance${NC}\n"

run_adaptive_test "variant_z" "python" "$PYTHON_PORT" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "java" "$JAVA_PORT" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "csharp" "$CSHARP_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 6: Nginx Health Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 6/9] Policy 4 Step 2 - Nginx Health Benchmark${NC}"
echo -e "${BLUE}Testing Nginx round-robin load balancing${NC}\n"

run_adaptive_test "variant_z" "nginx" "$NGINX_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 7: Individual Service Order Benchmarks (CRITICAL!)
# =============================================================================
echo -e "\n${YELLOW}[Step 7/9] Policy 4 Step 3 - Order Processing Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}*** CRITICAL: This tests CORE flash sale functionality with token pre-allocation! ***${NC}\n"

# Reset tokens before order benchmarks (to ensure we have enough for testing)
echo -e "${BLUE}Resetting tokens for order benchmarks...${NC}"
docker exec flash-python-z python -c "
import asyncio
from app.core.token_manager import token_manager
from app.core.database import async_session_maker

async def reset():
    async with async_session_maker() as session:
        # Get active campaigns
        from sqlalchemy import select
        from app.models.flash_sale import FlashSaleCampaign
        result = await session.execute(
            select(FlashSaleCampaign).where(FlashSaleCampaign.status == 'active')
        )
        campaigns = result.scalars().all()
        for campaign in campaigns:
            await token_manager.allocate_campaign_tokens(
                db=session,
                campaign_id=campaign.id,
                spu_id=campaign.spu_id,
                total_limit=campaign.total_sale_limit
            )
            print(f'Reset tokens for campaign {campaign.id}')

asyncio.run(reset())
" 2>/dev/null || echo -e "${YELLOW}⚠ Token reset skipped (may already be allocated)${NC}"

run_adaptive_test "variant_z" "python" "$PYTHON_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "java" "$JAVA_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "csharp" "$CSHARP_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 8: Nginx Order Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 8/9] Policy 4 Step 4 - Nginx Order Benchmark (Round-Robin)${NC}"
echo -e "${BLUE}Testing Nginx order processing with load balancing${NC}\n"

# Reset tokens again for Nginx test
docker exec flash-python-z python -c "
import asyncio
from app.core.token_manager import token_manager
from app.core.database import async_session_maker

async def reset():
    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.models.flash_sale import FlashSaleCampaign
        result = await session.execute(
            select(FlashSaleCampaign).where(FlashSaleCampaign.status == 'active')
        )
        campaigns = result.scalars().all()
        for campaign in campaigns:
            await token_manager.allocate_campaign_tokens(
                db=session,
                campaign_id=campaign.id,
                spu_id=campaign.spu_id,
                total_limit=campaign.total_sale_limit
            )

asyncio.run(reset())
" 2>/dev/null || true

run_adaptive_test "variant_z" "nginx" "$NGINX_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 9: Generate Summary
# =============================================================================
echo -e "\n${YELLOW}[Step 9/9] Generating pivot summary from CSV data...${NC}"

if [ -f "${SCRIPT_DIR}/../tools/generate_pivot_summary.py" ]; then
    python3 "${SCRIPT_DIR}/../tools/generate_pivot_summary.py" "$CSV_FILE"
    echo -e "${GREEN}✓ Pivot summary generated${NC}"
elif [ -f "${SCRIPT_DIR}/../generate_pivot_summary.py" ]; then
    python3 "${SCRIPT_DIR}/../generate_pivot_summary.py" "$CSV_FILE"
    echo -e "${GREEN}✓ Pivot summary generated${NC}"
else
    echo -e "${YELLOW}⚠ generate_pivot_summary.py not found, skipping pivot generation${NC}"
    echo -e "${BLUE}Raw CSV data available at: ${CSV_FILE}${NC}"
fi

# =============================================================================
# VARIANT Z VERIFICATION PASSED
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "              ✓ VARIANT Z VERIFICATION PASSED ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Variant Z (Token Pre-Allocation) verified successfully!${NC}"
echo ""
echo -e "${BLUE}Test Results:${NC}"
echo "  CSV Raw Data:    ${CSV_FILE}"
echo ""
echo -e "${BLUE}Variant Z Infrastructure:${NC}"
echo "  Python:  http://localhost:${PYTHON_PORT}"
echo "  Java:    http://localhost:${JAVA_PORT}"
echo "  C#:      http://localhost:${CSHARP_PORT}"
echo "  Nginx:   https://localhost:${NGINX_PORT}"
echo "  MariaDB: localhost:${MARIADB_PORT}"
echo ""
echo -e "${BLUE}Database Connection:${NC}"
echo "  Host: localhost"
echo "  Port: ${MARIADB_PORT}"
echo "  Database: orange315"
echo "  User: syracuse"
echo "  Password: Orange_315_Forever!"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  View CSV:        cat ${CSV_FILE} | column -t -s,"
echo "  Test order:      curl -X POST http://localhost:${PYTHON_PORT}/api/v1/orders -H 'Content-Type: application/json' -d '{\"customer_email\":\"test@example.com\",\"customer_name\":\"Test\",\"line_items\":[{\"sku_id\":\"<SKU_ID>\",\"quantity\":1}]}'"
echo ""

exit 0
