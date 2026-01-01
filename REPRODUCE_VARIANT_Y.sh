#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

DURATION="15s" # Default duration for benchmarks
REBUILD=false  # Set to true if you want to rebuild images

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}       REPRODUCE VARIANT Y (BASELINE) RESULTS       ${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo -e "Benchmark Duration: ${DURATION}"
echo -e "Rebuild services: ${REBUILD}"
echo ""

# -----------------------------------------------------------------------------
# 1. ENSURE MIDDLEWARE IS ON
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/5] Checking Middleware Services...${NC}"

if [ "$REBUILD" = true ]; then
    echo -e "${YELLOW}Rebuilding services...${NC}"
    podman-compose build
fi

# Ensure core infra is up
echo -e "${YELLOW}Starting services...${NC}"
podman-compose up -d --force-recreate
echo -e "${GREEN}Services start/recreate command issued.${NC}"

# Wait for MariaDB to be healthy
echo -e "${YELLOW}Waiting for MariaDB to be ready (Port 3307)...${NC}"
max_retries=30
count=0
while ! podman exec flash-mariadb mysqladmin ping -h localhost -u syracuse --password=Orange_315_Forever! --silent &> /dev/null; do
    sleep 2
    count=$((count+1))
    if [ $count -ge $max_retries ]; then
        echo -e "${RED}Timeout waiting for MariaDB!${NC}"
        exit 1
    fi
    echo -n "."
done
echo -e "\n${GREEN}✓ MariaDB is healthy.${NC}"

# -----------------------------------------------------------------------------
# 2. ENSURE APP SERVICES ARE ON
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[2/5] Verifying Application Services...${NC}"

# Wait for Health Checks
wait_for_health() {
    url=$1
    name=$2
    echo -n "Waiting for $name ($url)... "
    count=0
    while ! curl -s "$url" > /dev/null; do
        sleep 2
        count=$((count+1))
        if [ $count -ge 30 ]; then # Increased timeout for java/csharp cold starts
             echo -e "${RED}Timeout!${NC}"
             podman logs "flash-${name,,}" | tail -n 20
             exit 1
        fi
        echo -n "."
    done
    echo -e "${GREEN}OK${NC}"
}

wait_for_health "http://127.0.0.1:8000/health" "Python"
wait_for_health "http://127.0.0.1:8081/health" "Java"
wait_for_health "http://127.0.0.1:8082/health" "Csharp"

# -----------------------------------------------------------------------------
# 3. DATA SETUP
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[3/5] Setting up Test Data...${NC}"
# Use the setup script inside the python container
podman exec flash-python python /app/setup_test_data.py 500 5 10000

# Copy the SKU IDs out to the host for wrk to use
echo -e "${YELLOW}Copying SKU IDs to host...${NC}"
podman cp flash-python:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt

if [ -f /tmp/stress_test_sku_ids.txt ]; then
    count=$(wc -l < /tmp/stress_test_sku_ids.txt)
    echo -e "${GREEN}✓ SKU IDs copied. Total SKUs: $count${NC}"
else
    echo -e "${RED}Failed to copy SKU IDs!${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 4. FUNCTIONAL TESTS (LOGIC VERIFICATION)
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[4/5] Running Functional Tests (Pytest)...${NC}"
podman exec flash-python python -m pytest
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Logic verification passed.${NC}"
else
    echo -e "${RED}Logic verification FAILED!${NC}"
    exit 1
fi

# -----------------------------------------------------------------------------
# 5. PERFORMANCE BENCHMARKS
# -----------------------------------------------------------------------------
echo -e "\n${YELLOW}[5/5] Running Performance Benchmarks (Duration: $DURATION)${NC}"
echo "Waiting 5s for services to settle..."
sleep 5

run_wrk() {
    desc=$1
    shift
    echo -e "\n${BLUE}>>> $desc${NC}"
    echo "Command: $@"
    "$@"
    sleep 2
}

# --- HEALTH ---
echo -e "\n${YELLOW}--- Baseline: Health Endpoints ---${NC}"
run_wrk "Python Health" wrk -t12 -c100 -d$DURATION http://127.0.0.1:8000/health
run_wrk "Java Health"   wrk -t12 -c200 -d$DURATION http://127.0.0.1:8081/health
run_wrk "C# Health"     wrk -t12 -c600 -d$DURATION http://127.0.0.1:8082/health

# --- ORDERS (Direct) ---
echo -e "\n${YELLOW}--- Business Logic: Orders (Direct) ---${NC}"
run_wrk "Python Orders" wrk -t12 -c50 -d$DURATION --latency -s python-service/wrk_order_script.lua http://127.0.0.1:8000/api/v1/orders
run_wrk "Java Orders"   wrk -t12 -c75 -d$DURATION --latency -s java-service/wrk_order_script.lua http://127.0.0.1:8081/api/v1/orders
run_wrk "C# Orders"     wrk -t12 -c25 -d$DURATION --latency -s csharp-service/wrk_order_script.lua http://127.0.0.1:8082/api/v1/orders

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${GREEN}       REPRODUCTION COMPLETE       ${NC}"
echo -e "${GREEN}========================================================================${NC}
