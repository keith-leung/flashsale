#!/bin/bash
# Comprehensive verification script for Variant V - All Services

echo "=== Variant V - All Services Verification ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3
    
    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" $url 2>/dev/null)
    
    if [ "$response" == "$expected" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
        ((passed++))
    else
        echo -e "${RED}FAIL${NC} (expected HTTP $expected, got HTTP $response)"
        ((failed++))
    fi
}

# Check container health
echo "Checking container status..."
docker ps | grep flash- | awk '{print $NF}' | while read container; do
    status=$(docker inspect $container --format='{{.State.Status}}' 2>/dev/null)
    health=$(docker inspect $container --format='{{.State.Health.Status}}' 2>/dev/null || echo "no health check")
    if [ "$status" = "running" ]; then
        echo -e "  ${GREEN}✓${NC} $container (running)"
    else
        echo -e "  ${RED}✗${NC} $container ($status)"
        ((failed++))
    fi
done
echo ""

# Test individual services
echo "Testing individual service health endpoints..."
test_endpoint "Python Service" "http://localhost:30017/health" "200"
test_endpoint "Java Service" "http://localhost:8018/health" "200"
test_endpoint "C# Service" "http://localhost:30016/health" "200"
echo ""

# Test Nginx load balancer
echo "Testing Nginx load balancer..."
test_endpoint "Nginx LB" "http://localhost:8447/health" "200"
echo ""

# Test Redis nodes
echo "Testing Redis nodes..."
for i in 1 2 3; do
    echo -n "Testing Redis node $i... "
    if docker exec flash-redis${i}-v redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC} (PONG)"
        ((passed++))
    else
        echo -e "${RED}FAIL${NC} (no response)"
        ((failed++))
    fi
done
echo ""

# Test MariaDB
echo -n "Testing MariaDB... "
if docker exec flash-mariadb-v mysql -u syracuse -pOrange_315_Forever! -e "SELECT 1" orange315 > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    ((passed++))
else
    echo -e "${RED}FAIL${NC}"
    ((failed++))
fi
echo ""

# Summary
echo ""
echo "=== Verification Summary ==="
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"

if [ $failed -eq 0 ]; then
    echo -e "\n${GREEN}✓ All services verified successfully!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some services failed verification${NC}"
    exit 1
fi
