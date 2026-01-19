#!/bin/bash
# =============================================================================
# VARIANT Z BENCHMARK - Token Pre-Allocation Architecture
# =============================================================================
# This script benchmarks Variant Z using the same adaptive plateau detection
# methodology as SACRED_VERIFICATION for fair comparison with Variant Y.
#
# Usage: bash benchmark_variant_z.sh [DURATION]
# =============================================================================

set -e

# Configuration
DURATION="${1:-10}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="../benchmark_results"
CSV_FILE="${RESULTS_DIR}/variant_Z_raw_${TIMESTAMP}.csv"

# Variant Z ports
PYTHON_PORT="30017"
JAVA_PORT="8019"
CSHARP_PORT="30018"
NGINX_PORT="8448"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "                   VARIANT Z BENCHMARK"
echo "           Token Pre-Allocation Architecture"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo -e "${BLUE}Testing Mode: FULL (Adaptive Plateau Detection)${NC}"
echo -e "${BLUE}Base Duration: ${DURATION}s${NC}"
echo -e "${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

# =============================================================================
# Step 1: Ensure Services Are Running
# =============================================================================
echo -e "${YELLOW}[Step 1/6] Checking Variant Z services...${NC}"

CONTAINERS=("flash-mariadb-z" "flash-redis-z" "flash-python-z" "flash-java-z" "flash-csharp-z" "flash-nginx-z")
RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        RUNNING=false
        break
    fi
done

if [ "$RUNNING" = false ]; then
    echo -e "${RED}✗ Some services not running, starting...${NC}"
    docker compose up -d
    echo -e "${YELLOW}Waiting 60s for services to initialize...${NC}"
    sleep 60
else
    echo -e "${GREEN}✓ All services running${NC}"
fi

# =============================================================================
# Step 2: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 2/6] Running health checks...${NC}"

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
    exit 1
}

check_health "Python" "$PYTHON_PORT"
check_health "Java" "$JAVA_PORT"
check_health "C#" "$CSHARP_PORT"

# Check database
if docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MariaDB connection OK${NC}"
else
    echo -e "${RED}✗ MariaDB connection FAILED${NC}"
    exit 1
fi

# Check Redis
if docker exec flash-redis-z redis-cli PING > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis connection OK${NC}"
else
    echo -e "${RED}✗ Redis connection FAILED${NC}"
    exit 1
fi

# =============================================================================
# Step 3: Prepare Test Data and CSV
# =============================================================================
echo -e "\n${YELLOW}[Step 3/6] Preparing test data and CSV output...${NC}"

mkdir -p "$RESULTS_DIR"

# Initialize CSV
cat > "$CSV_FILE" << 'EOF'
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
EOF

echo -e "${GREEN}✓ CSV initialized: ${CSV_FILE}${NC}"

# Ensure test data exists
if [ ! -f /tmp/stress_test_sku_ids.txt ]; then
    echo -e "${BLUE}Generating test data (500 SPUs, 2500 SKUs)...${NC}"
    docker exec flash-python-z python /app/setup_test_data.py 500 5 10000 > /dev/null 2>&1
    docker cp flash-python-z:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt 2>/dev/null || true
    echo -e "${GREEN}✓ Test data generated${NC}"
else
    echo -e "${GREEN}✓ Test data already exists${NC}"
fi

# Copy benchmark script for variant-Z
if [ ! -f /tmp/order_benchmark.lua ]; then
    if [ -f wrk_order_script.lua ]; then
        cp wrk_order_script.lua /tmp/order_benchmark.lua
        echo -e "${GREEN}✓ Order benchmark script copied from variant-z${NC}"
    elif [ -f python-service/wrk_order_script.lua ]; then
        cp python-service/wrk_order_script.lua /tmp/order_benchmark.lua
        echo -e "${GREEN}✓ Order benchmark script copied from python-service${NC}"
    elif [ -f ../python-service/wrk_order_script.lua ]; then
        cp ../python-service/wrk_order_script.lua /tmp/order_benchmark.lua
        echo -e "${GREEN}✓ Order benchmark script copied from parent python-service${NC}"
    else
        echo -e "${RED}✗ wrk_order_script.lua not found${NC}"
        echo -e "${RED}BENCHMARK FAILED: Missing benchmark script${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Order benchmark script already exists${NC}"
fi

# Source plateau detection library
source ../lib/plateau_detector.sh

# =============================================================================
# Step 4: Health Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}[Step 4/6] Health Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}Using adaptive plateau detection to find optimal performance${NC}\n"

run_adaptive_test "variant_z" "python" "$PYTHON_PORT" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "java" "$JAVA_PORT" "/health" "health" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "csharp" "$CSHARP_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 5: Nginx Health Benchmark
# =============================================================================
echo -e "\n${YELLOW}[Step 5/6] Nginx Health Benchmark${NC}"
echo -e "${BLUE}Testing Nginx round-robin load balancing${NC}\n"

run_adaptive_test "variant_z" "nginx" "$NGINX_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# =============================================================================
# Step 6: Order Processing Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}[Step 6/6] Order Processing Benchmarks (Direct Access)${NC}"
echo -e "${BLUE}*** CRITICAL: Testing core flash sale functionality! ***${NC}\n"

run_adaptive_test "variant_z" "python" "$PYTHON_PORT" "/api/v1/orders/" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "java" "$JAVA_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"
run_adaptive_test "variant_z" "csharp" "$CSHARP_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Generate Summary
# =============================================================================
echo -e "\n${YELLOW}Generating summary from CSV data...${NC}"

if [ -f "../generate_pivot_summary.py" ]; then
    python3 ../generate_pivot_summary.py "$CSV_FILE"
    echo -e "${GREEN}✓ Pivot summary generated${NC}"
else
    echo -e "${YELLOW}⚠ generate_pivot_summary.py not found${NC}"
fi

# =============================================================================
# BENCHMARK COMPLETE
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "              ✓ VARIANT Z BENCHMARK COMPLETE ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Variant Z (Token Pre-Allocation) benchmarked successfully${NC}"
echo ""
echo -e "${BLUE}Test Results:${NC}"
echo "  CSV Raw Data:    ${CSV_FILE}"
echo ""

exit 0