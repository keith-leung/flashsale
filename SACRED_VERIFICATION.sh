#!/bin/bash
# =============================================================================
# SACRED VERIFICATION.sh - THE SACRED VERIFICATION Testing Script
# =============================================================================
# This is THE SACRED VERIFICATION script for the ENTIRE repository
#
# CRITICAL: DO NOT EDIT THIS SCRIPT TO TEST YOUR NEW VARIANT
# CRITICAL: DO NOT RUN THIS SCRIPT TO TEST YOUR NEW VARIANT
#
# This script is FOR VARIANT Y (BASELINE) ONLY
#
# For Variant X, Z, or any other variant:
#   1. DO NOT USE THIS SCRIPT
#   2. DO NOT EDIT THIS SCRIPT
#   3. CREATE YOUR OWN variant-specific script
#   4. USE SAME ADAPTIVE ALGORITHM (but different ports/services)
#   5. USE SAME CSV SCHEMA (27 fields)
#   6. USE SAME TESTING METHODOLOGY (adaptive plateau detection)
#
# Why: All variants must use SAME methodology to enable performance comparison
#       Different test methodologies = incomparable results
#       This script produces THE SACRED CSV schema that all variants must match
#
# Version: 2.0
# Date: 2026-01-15
# Status: ✅ IMPLEMENTED (Variant Y only - all other variants must create their own)
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
DURATION="${1:-10}"  # Default 10s per test
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./benchmark_results"
VARIANT_NAME=""

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# Variant Service Mappings
# =============================================================================
# Each variant has its own services, ports, and configurations
# CRITICAL: Variants MUST NOT share ports, databases, or Redis instances
# =============================================================================

case "${2:-}" in
    variant_y)
        VARIANT_NAME="variant_y"
        PYTHON_SERVICE="flash-python-y"
        JAVA_SERVICE="flash-java-y"
        CSHARP_SERVICE="flash-csharp-y"
        NGINX_SERVICE="flash-nginx-y"
        PYTHON_PORT="30017"
        JAVA_PORT="8019"
        CSHARP_PORT="30018"
        NGINX_PORT="8448"
        REDIS_SERVICE="flash-redis-y"
        MARIADB_SERVICE="flash-mariadb-y"
        ;;
    variant_z)
        VARIANT_NAME="variant_z"
        PYTHON_SERVICE="flash-python-api-zeta"
        JAVA_SERVICE="flash-java-z"
        CSHARP_SERVICE="flash-csharp-z"
        NGINX_SERVICE="flash-nginx-z"
        PYTHON_PORT="30019"
        JAVA_PORT="8019"
        CSHARP_PORT="30018"
        NGINX_PORT="8448"
        REDIS_SERVICE="flash-redis-zeta"
        MARIADB_SERVICE="flash-mariadb-zeta"
        ;;
    *)
        echo -e "${RED}✗ Invalid variant: ${2:-}${NC}"
        echo -e "${YELLOW}Valid variants: variant_y, variant_z${NC}"
        exit 1
        ;;
esac

CSV_FILE="${RESULTS_DIR}/${VARIANT_NAME}_raw_${TIMESTAMP}.csv"

# =============================================================================
# Banner
# =============================================================================
echo -e "${BOLD}${BLUE}"
echo "═════════════════════════════════════════════════════════════════"
echo "           SACRED VERIFICATION Testing"
echo "         THE SACRED VERIFICATION Testing Script"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${BOLD}${BLUE}Variant: ${VARIANT_NAME}${NC}"
echo -e "${BOLD}${BLUE}Mode: FULL (Adaptive Plateau Detection)${NC}"
echo -e "${BOLD}${BLUE}Base Duration: ${DURATION}s${NC}"
echo -e "${BOLD}${BLUE}Results: ${CSV_FILE}${NC}"
echo ""

# =============================================================================
# Check if running as correct variant
# =============================================================================
echo -e "${YELLOW}[1/5] Checking variant configuration...${NC}"

if [ -n "${2:-}" ]; then
    echo -e "${GREEN}  ✓ Using provided variant: ${VARIANT_NAME}${NC}"
else
    echo -e "${RED}  ✗ Variant name required${NC}"
    echo -e "${YELLOW}  Usage: bash SACRED_VERIFICATION.sh <duration> <variant_name>${NC}"
    echo -e "${YELLOW}  Examples:${NC}"
    echo -e "${YELLOW}    bash SACRED_VERIFICATION.sh 10 variant_y${NC}"
    echo -e "${YELLOW}    bash SACRED_VERIFICATION.sh 30 variant_z${NC}"
    exit 1
fi

# =============================================================================
# Ensure Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[2/5] Ensuring ${VARIANT_NAME} services are running...${NC}"

CONTAINERS=("$PYTHON_SERVICE" "$JAVA_SERVICE" "$CSHARP_SERVICE" "$NGINX_SERVICE")
NEED_START=false

for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        NEED_START=true
        break
    fi
done

if [ "$NEED_START" = true ]; then
    echo -e "${YELLOW}  ✗ Some services are not running${NC}"
    echo -e "${YELLOW}  Please ensure all ${VARIANT_NAME} services are started${NC}"
    exit 1
else
    echo -e "${GREEN}  ✓ All services already running${NC}"
fi

# Verify all containers are up
echo -e "${BLUE}  Container Status:${NC}"
for container in "${CONTAINERS[@]}"; do
    STATUS=$(docker ps --filter "name=^${container}$" --format "{{.Status}}" 2>/dev/null || echo "NOT RUNNING")
    if [[ "$STATUS" == "Up"* ]]; then
        echo -e "${GREEN}    ✓ ${container}: ${STATUS}${NC}"
    else
        echo -e "${RED}    ✗ ${container}: ${STATUS}${NC}"
        exit 1
    fi
done

# =============================================================================
# Health Checks
# =============================================================================
echo -e "\n${YELLOW}[3/5] Running health checks...${NC}"

PYTHON_ENDPOINT="http://localhost:${PYTHON_PORT}"
JAVA_ENDPOINT="http://localhost:${JAVA_PORT}"
CSHARP_ENDPOINT="http://localhost:${CSHARP_PORT}"
NGINX_ENDPOINT="http://localhost:${NGINX_PORT}"

# Check Python
echo -e "${BLUE}  Checking Python API...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${PYTHON_ENDPOINT}/health" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Python API: OK${NC}"
else
    echo -e "${RED}    ✗ Python API: FAILED${NC}"
    exit 1
fi

# Check Java
echo -e "${BLUE}  Checking Java API...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${JAVA_ENDPOINT}/actuator/health" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Java API: OK${NC}"
else
    echo -e "${RED}    ✗ Java API: FAILED${NC}"
    exit 1
fi

# Check C#
echo -e "${BLUE}  Checking C# API...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${CSHARP_ENDPOINT}/health" | grep -q "200"; then
    echo -e "${GREEN}    ✓ C# API: OK${NC}"
else
    echo -e "${RED}    ✗ C# API: FAILED${NC}"
    exit 1
fi

# Check Nginx
echo -e "${BLUE}  Checking Nginx...${NC}"
if curl -sf -o /dev/null -w "%{http_code}" "${NGINX_ENDPOINT}/health" | grep -q "200"; then
    echo -e "${GREEN}    ✓ Nginx: OK${NC}"
else
    echo -e "${RED}    ✗ Nginx: FAILED${NC}"
    exit 1
fi

# =============================================================================
# Initialize CSV
# =============================================================================
echo -e "\n${YELLOW}[4/5] Initializing CSV...${NC}"

mkdir -p "$RESULTS_DIR"

echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "$CSV_FILE"

echo -e "${GREEN}  ✓ CSV initialized: ${CSV_FILE}${NC}"

# =============================================================================
# Run Adaptive Plateau Detection Tests
# =============================================================================
echo -e "\n${YELLOW}[5/5] Running adaptive plateau detection tests...${NC}"

# Test Python
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: Python (${PYTHON_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# Python /health
echo -e "${BOLD}${BLUE}[Python] Test 1: /health endpoint${NC}"
bash ./lib/plateau_detector.sh "$PYTHON_ENDPOINT" "/health" "health" "$PYTHON_SERVICE" "$CSV_FILE" "$DURATION"

# Python /orders
echo -e "\n${BOLD}${BLUE}[Python] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$PYTHON_ENDPOINT" "/orders/" "order" "$PYTHON_SERVICE" "$CSV_FILE" "$DURATION"

# Test Java
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: Java (${JAVA_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# Java /health
echo -e "${BOLD}${BLUE}[Java] Test 1: /actuator/health endpoint${NC}"
bash ./lib/plateau_detector.sh "$JAVA_ENDPOINT" "/actuator/health" "health" "$JAVA_SERVICE" "$CSV_FILE" "$DURATION"

# Java /orders
echo -e "\n${BOLD}${BLUE}[Java] Test 2: /api/v1/orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$JAVA_ENDPOINT" "/api/v1/orders" "order" "$JAVA_SERVICE" "$CSV_FILE" "$DURATION"

# Test C#
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: C# (${CSHARP_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# C# /health
echo -e "${BOLD}${BLUE}[C#] Test 1: /health endpoint${NC}"
bash ./lib/plateau_detector.sh "$CSHARP_ENDPOINT" "/health" "health" "$CSHARP_SERVICE" "$CSV_FILE" "$DURATION"

# C# /orders
echo -e "\n${BOLD}${BLUE}[C#] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$CSHARP_ENDPOINT" "/orders" "order" "$CSHARP_SERVICE" "$CSV_FILE" "$DURATION"

# Test Nginx
echo -e "\n${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo -e "${BOLD}${BLUE}Testing: Nginx (${NGINX_SERVICE})${NC}"
echo -e "${BOLD}${BLUE}═════════════════════════════════════════════${NC}"
echo ""

# Nginx /health
echo -e "${BOLD}${BLUE}[Nginx] Test 1: /health endpoint${NC}"
bash ./lib/plateau_detector.sh "$NGINX_ENDPOINT" "/health" "health" "$NGINX_SERVICE" "$CSV_FILE" "$DURATION"

# Nginx /orders
echo -e "\n${BOLD}${BLUE}[Nginx] Test 2: /orders endpoint${NC}"
bash ./lib/plateau_detector.sh "$NGINX_ENDPOINT" "/orders" "order" "$NGINX_SERVICE" "$CSV_FILE" "$DURATION"

# =============================================================================
# Generate Summary
# =============================================================================
echo -e "\n${YELLOW}Generating pivot summary...${NC}"
python3 ./generate_pivot_summary.py "$CSV_FILE"

# =============================================================================
# Complete
# =============================================================================
echo -e "\n${BOLD}${GREEN}"
echo "═════════════════════════════════════════════════════════════════"
echo "         ✓ SACRED VERIFICATION PASSED ✓"
echo "═════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}CSV Raw Data: ${CSV_FILE}${NC}"
echo -e "${GREEN}Pivot Summary: ./benchmark_results/summary_${TIMESTAMP}.md${NC}"

exit 0
