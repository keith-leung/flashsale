#!/bin/bash
# =============================================================================
# Variant A Adaptive Testing Script (SACRED VERIFICATION Methodology)
# =============================================================================
# This script applies the SACRED VERIFICATION adaptive plateau detection
# methodology to Variant A.
#
# Methodology:
#   1. Adaptive Plateau Detection (lib/plateau_detector.sh)
#   2. Sacred CSV Schema (27 fields)
#   3. Standard Test Sequence (Health -> Orders)
#
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
DURATION="${1:-10}"  # Default 10s per test
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./benchmark_results"
VARIANT_NAME="variant_a"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# Variant A Service Mappings
# =============================================================================
PYTHON_SERVICE="flash-python-a"
JAVA_SERVICE="flash-java-a"
CSHARP_SERVICE="flash-csharp-a"
NGINX_SERVICE="flash-nginx-a"

PYTHON_PORT="30013"
JAVA_PORT="8017"
CSHARP_PORT="30014"
NGINX_PORT="8446"

# Endpoints
PYTHON_HEALTH_URL="http://localhost:${PYTHON_PORT}/health"
PYTHON_ORDER_URL="http://localhost:${PYTHON_PORT}/api/v1/orders"

JAVA_HEALTH_URL="http://localhost:${JAVA_PORT}/health"
JAVA_ORDER_URL="http://localhost:${JAVA_PORT}/api/v1/orders"

CSHARP_HEALTH_URL="http://localhost:${CSHARP_PORT}/health"
CSHARP_ORDER_URL="http://localhost:${CSHARP_PORT}/api/v1/orders"

NGINX_HEALTH_URL="https://localhost:${NGINX_PORT}/health"
NGINX_ORDER_URL="https://localhost:${NGINX_PORT}/api/v1/orders"

CSV_FILE="${RESULTS_DIR}/${VARIANT_NAME}_raw_${TIMESTAMP}.csv"

# =============================================================================
# Banner
# =============================================================================
echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "           Variant A Adaptive Testing"
echo "         Applying SACRED VERIFICATION Methodology"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BOLD}${BLUE}Variant: ${VARIANT_NAME}${NC}"
echo -e "${BOLD}${BLUE}Mode: FULL (Adaptive Plateau Detection)${NC}"
echo -e "${BOLD}${BLUE}Base Duration: ${DURATION}s${NC}"
echo -e "${BOLD}${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

# =============================================================================
# Ensure Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[1/4] Ensuring ${VARIANT_NAME} services are running...${NC}"

CONTAINERS=("$PYTHON_SERVICE" "$JAVA_SERVICE" "$CSHARP_SERVICE" "$NGINX_SERVICE")
NEED_START=false

for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        NEED_START=true
        echo -e "${RED}  ✗ ${container}: NOT RUNNING${NC}"
    else
        echo -e "${GREEN}  ✓ ${container}: RUNNING${NC}"
    fi
done

if [ "$NEED_START" = true ]; then
    echo -e "${YELLOW}  Some services are not running. Please start Variant A first.${NC}"
    exit 1
fi

# =============================================================================
# Health Checks
# =============================================================================
echo -e "\n${YELLOW}[2/4] Running health checks...${NC}"

# Check Python
echo -e "${BLUE}  Checking Python API...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${PYTHON_HEALTH_URL}" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Python API: OK${NC}"
else
    echo -e "${RED}    ✗ Python API: FAILED (${PYTHON_HEALTH_URL})${NC}"
    exit 1
fi

# Check Java
echo -e "${BLUE}  Checking Java API...${NC}"
# Try /health first
if curl -sf -o /dev/null -w "%{http_code}" "${JAVA_HEALTH_URL}" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Java API: OK${NC}"
else
    # Fallback to /actuator/health if needed
    JAVA_HEALTH_URL="http://localhost:${JAVA_PORT}/actuator/health"
    if curl -sf -o /dev/null -w "%{http_code}" "${JAVA_HEALTH_URL}" | grep -q "200"; then
        echo -e "${GREEN}    ✓ Java API: OK (via /actuator/health)${NC}"
    else
        echo -e "${RED}    ✗ Java API: FAILED${NC}"
        exit 1
    fi
fi

# Check C#
echo -e "${BLUE}  Checking C# API...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${CSHARP_HEALTH_URL}" | grep -q "200"; then
    echo -e "${GREEN}    ✓ C# API: OK${NC}"
else
    echo -e "${RED}    ✗ C# API: FAILED${NC}"
    exit 1
fi

# Check Nginx (HTTPS, insecure for local certs)
echo -e "${BLUE}  Checking Nginx...${NC}"
if curl -k -sf -o /dev/null -w "%{http_code}" "${NGINX_HEALTH_URL}" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Nginx: OK${NC}"
else
    echo -e "${RED}    ✗ Nginx: FAILED${NC}"
    exit 1
fi

# =============================================================================
# Initialize CSV
# =============================================================================
echo -e "\n${YELLOW}[3/4] Initializing CSV...${NC}"

mkdir -p "$RESULTS_DIR"

echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "$CSV_FILE"

echo -e "${GREEN}  ✓ CSV initialized: ${CSV_FILE}${NC}"

# =============================================================================
# Run Adaptive Plateau Detection Tests
# =============================================================================
echo -e "\n${YELLOW}[4/4] Running adaptive plateau detection tests...${NC}"

# Test Python
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: Python (${PYTHON_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# Python /health
echo -e "${BOLD}${BLUE}[Python] Test 1: /health endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$PYTHON_SERVICE" "$PYTHON_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# Python /orders
echo -e "\n${BOLD}${BLUE}[Python] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$PYTHON_SERVICE" "$PYTHON_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# Test Java
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: Java (${JAVA_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# Java /health
if [[ "$JAVA_HEALTH_URL" == *"/actuator/health"* ]]; then
    JAVA_HEALTH_PATH="/actuator/health"
else
    JAVA_HEALTH_PATH="/health"
fi
echo -e "${BOLD}${BLUE}[Java] Test 1: ${JAVA_HEALTH_PATH} endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$JAVA_SERVICE" "$JAVA_PORT" "$JAVA_HEALTH_PATH" "health" "$DURATION" "$CSV_FILE"

# Java /orders
echo -e "\n${BOLD}${BLUE}[Java] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$JAVA_SERVICE" "$JAVA_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# Test C#
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: C# (${CSHARP_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# C# /health
echo -e "${BOLD}${BLUE}[C#] Test 1: /health endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$CSHARP_SERVICE" "$CSHARP_PORT" "/health" "health" "$DURATION" "$CSV_FILE"

# C# /orders
echo -e "\n${BOLD}${BLUE}[C#] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$VARIANT_NAME" "$CSHARP_SERVICE" "$CSHARP_PORT" "/api/v1/orders" "order" "$DURATION" "$CSV_FILE"

# =============================================================================
# Generate Summary
# =============================================================================
echo -e "\n${YELLOW}Generating pivot summary...${NC}"
python3 ./tools/generate_pivot_summary.py "$CSV_FILE"

# =============================================================================
# Complete
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "         ✓ VARIANT A ADAPTIVE TEST COMPLETE ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}CSV Raw Data: ${CSV_FILE}${NC}"
echo -e "${GREEN}Pivot Summary: ./benchmark_results/summary_${TIMESTAMP}.md${NC}"

exit 0
