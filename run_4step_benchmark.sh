#!/bin/bash
# =============================================================================
# 4-Step Functionality Benchmark - Idempotent & Reproducible
# =============================================================================
# This script ensures all services are running before executing benchmarks.
# Can be run by any agent or human without context - reads state from system.
#
# Usage: bash run_4step_benchmark.sh [quick|full]
#   quick: 10s duration for fast verification
#   full:  30s duration for accurate metrics (default)
#
# Prerequisites:
#   - wrk installed (HTTP benchmarking tool)
#   - podman-compose installed
#   - docker-compose.yml in current directory
# =============================================================================

set -e  # Exit on error

# Configuration
DURATION=${1:-full}
if [ "$DURATION" = "quick" ]; then
    TEST_DURATION="10s"
    echo "=== QUICK MODE: 10s test duration ==="
else
    TEST_DURATION="30s"
    echo "=== FULL MODE: 30s test duration ==="
fi

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# =============================================================================
# Step 0: Ensure all services are running
# =============================================================================
echo -e "\n${YELLOW}[Step 0] Checking service status...${NC}"

# Check if containers exist and are running
CONTAINERS=("flash-mariadb" "flash-redis" "flash-python" "flash-java" "flash-csharp" "flash-nginx")
ALL_RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if ! podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo -e "${RED}✗ ${container} is not running${NC}"
        ALL_RUNNING=false
    else
        echo -e "${GREEN}✓ ${container} is running${NC}"
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo -e "\n${YELLOW}Starting services with podman-compose...${NC}"
    podman-compose up -d

    echo -e "${YELLOW}Waiting 30s for services to initialize...${NC}"
    sleep 30

    echo -e "${GREEN}Services started!${NC}"
else
    echo -e "${GREEN}All services already running!${NC}"
fi

# Verify health endpoints respond
echo -e "\n${YELLOW}Verifying service health...${NC}"
for i in {1..10}; do
    if curl -sf http://localhost:8000/health > /dev/null && \
       curl -sf http://localhost:8081/health > /dev/null && \
       curl -sf http://localhost:8082/health > /dev/null; then
        echo -e "${GREEN}✓ All services healthy${NC}"
        break
    fi

    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Services not responding after 10 retries${NC}"
        exit 1
    fi

    echo "Waiting for services... ($i/10)"
    sleep 3
done

# =============================================================================
# Step 1: Individual Service Health Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}[Step 1] Health Check - Direct Access${NC}"
echo -e "${YELLOW}========================================${NC}"

echo -e "\n${GREEN}Testing Python (localhost:8000/health) - Optimal: -c100${NC}"
wrk -t12 -c100 -d${TEST_DURATION} --latency http://localhost:8000/health

echo -e "\n${GREEN}Testing Java (localhost:8081/health) - Optimal: -c200${NC}"
wrk -t12 -c200 -d${TEST_DURATION} --latency http://localhost:8081/health

echo -e "\n${GREEN}Testing C# (localhost:8082/health) - Optimal: -c600${NC}"
wrk -t12 -c600 -d${TEST_DURATION} --latency http://localhost:8082/health

# =============================================================================
# Step 2: Nginx Health Benchmark (Load Balancer)
# =============================================================================
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}[Step 2] Health Check - Via Nginx${NC}"
echo -e "${YELLOW}========================================${NC}"

echo -e "\n${GREEN}Testing Nginx Round-Robin (https://localhost:8443/health) - Optimal: -c25${NC}"
wrk -t12 -c25 -d${TEST_DURATION} --latency https://localhost:8443/health

# =============================================================================
# Step 3: Individual Service Order Benchmarks (Direct Access)
# =============================================================================
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}[Step 3] Order Processing - Direct Access${NC}"
echo -e "${YELLOW}========================================${NC}"

# Ensure test data exists
if [ ! -f /tmp/stress_test_sku_ids.txt ]; then
    echo -e "${YELLOW}Generating test data (500 SPUs, 2500 SKUs)...${NC}"
    podman exec flash-python python /app/setup_test_data.py 500 5 10000
    podman cp flash-python:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt
    echo -e "${GREEN}Test data generated!${NC}"
else
    echo -e "${GREEN}Test data already exists${NC}"
fi

# Copy benchmark script to /tmp for wrk
if [ ! -f /tmp/order_benchmark.lua ]; then
    if [ -f python-service/wrk_order_script.lua ]; then
        cp python-service/wrk_order_script.lua /tmp/order_benchmark.lua
    else
        echo -e "${RED}Error: wrk_order_script.lua not found${NC}"
        exit 1
    fi
fi

echo -e "\n${GREEN}Testing Python Orders (localhost:8000/api/v1/orders) - Optimal: -c50${NC}"
wrk -t12 -c50 -d${TEST_DURATION} --latency -s /tmp/order_benchmark.lua http://localhost:8000/api/v1/orders

echo -e "\n${GREEN}Testing Java Orders (localhost:8081/api/v1/orders) - Optimal: -c75${NC}"
wrk -t12 -c75 -d${TEST_DURATION} --latency -s /tmp/order_benchmark.lua http://localhost:8081/api/v1/orders

echo -e "\n${GREEN}Testing C# Orders (localhost:8082/api/v1/orders) - Optimal: -c25${NC}"
wrk -t12 -c25 -d${TEST_DURATION} --latency -s /tmp/order_benchmark.lua http://localhost:8082/api/v1/orders

# =============================================================================
# Step 4: Nginx Order Benchmark (Load Balancer)
# =============================================================================
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}[Step 4] Order Processing - Via Nginx${NC}"
echo -e "${YELLOW}========================================${NC}"

echo -e "\n${GREEN}Testing Nginx Round-Robin Orders (https://localhost:8443/api/v1/orders) - Optimal: -t4 -c50${NC}"
wrk -t4 -c50 -d${TEST_DURATION} --latency -s /tmp/order_benchmark.lua https://localhost:8443/api/v1/orders

# =============================================================================
# Summary
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}4-Step Benchmark Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review results above"
echo "  2. Compare with baseline in README.md"
echo "  3. Run unit tests: podman exec flash-python python -m pytest"
echo ""
echo "DataGrip connection:"
echo "  Host: localhost"
echo "  Port: 3307"
echo "  Database: orange315"
echo "  User: syracuse"
echo "  Password: Orange_315_Forever!"
