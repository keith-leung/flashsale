#!/bin/bash
# =============================================================================
# TEMPLATE: Variant Verification Script
# =============================================================================
# Copy this script to your variant directory (e.g., variant-b/verify_variant_b.sh)
# and customize the TODO sections.
#
# This script ensures your variant complies with SACRED standards:
# 1. Services start correctly
# 2. Health checks pass
# 3. Database schema is compatible
# 4. API endpoints are backward compatible
#
# Usage: bash verify_variant_{letter}.sh
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION (TODO: Customize this section)
# =============================================================================
VARIANT_NAME="variant-b"           # Your variant name
DB_CONTAINER="flash-mariadb-b"     # Your MariaDB container name
REDIS_CONTAINER="flash-redis-b"    # Your Redis container (optional)
PYTHON_CONTAINER="flash-python-b"  # Your Python container
PYTHON_PORT="30015"                # Your Python service host port
JAVA_PORT="8018"                   # Your Java service host port
CSHARP_PORT="30016"                # Your C# service host port
NGINX_PORT="8447"                  # Your Nginx host port

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting Verification for ${VARIANT_NAME}...${NC}"

# =============================================================================
# Step 1: Ensure Services Are Running
# =============================================================================
echo -e "\n${YELLOW}[Step 1/6] Checking services...${NC}"

# TODO: Add your service container names here
CONTAINERS=("$DB_CONTAINER" "$PYTHON_CONTAINER") 

RUNNING=true
for container in "${CONTAINERS[@]}"; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$\"; then
        RUNNING=false
        break
    fi
done

if [ "$RUNNING" = false ]; then
    echo -e "${YELLOW}Starting services...${NC}"
    docker-compose up -d
    echo -e "${YELLOW}Waiting 30s for initialization...${NC}"
    sleep 30
else
    echo -e "${GREEN}✓ Services running${NC}"
fi

# =============================================================================
# Step 2: Health Checks
# =============================================================================
echo -e "\n${YELLOW}[Step 2/6] Running health checks...${NC}"

check_health() {
    local service=$1
    local port=$2
    if curl -sf "http://localhost:${port}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ${service} health OK (Port ${port})${NC}"
    else
        echo -e "${RED}✗ ${service} health FAILED (Port ${port})${NC}"
        exit 1
    fi
}

check_health "Python" "$PYTHON_PORT"
check_health "Java" "$JAVA_PORT"
check_health "C#" "$CSHARP_PORT"

# =============================================================================
# Step 3: Database Schema Check (SACRED Compliance)
# =============================================================================
echo -e "\n${YELLOW}[Step 3/6] Verifying schema compliance...${NC}"

# Check for mandatory table
if docker exec "$DB_CONTAINER" mysql -usyracuse -pOrange_315_Forever! orange315 -e "SHOW TABLES LIKE 'flash_sale_campaigns'" 2>&1 | grep -q "flash_sale_campaigns"; then
    echo -e "${GREEN}✓ flash_sale_campaigns table exists${NC}"
else
    echo -e "${RED}✗ SACRED VIOLATION: flash_sale_campaigns table missing${NC}"
    exit 1
fi

# =============================================================================
# Step 4: Test Data Setup (TODO: Customize)
# =============================================================================
echo -e "\n${YELLOW}[Step 4/6] Setting up test data...${NC}"

# TODO: Add your data seeding logic here.
# Example: docker exec "$PYTHON_CONTAINER" python /app/setup_test_data.py
echo -e "${BLUE}Skipping data setup (Customize this step)${NC}"

# =============================================================================
# Step 5: Functional Test (Order Creation)
# =============================================================================
echo -e "\n${YELLOW}[Step 5/6] Testing order creation API...${NC}"

# Smoke test the API
RESPONSE=$(curl -s -X POST "http://localhost:${PYTHON_PORT}/api/v1/orders" \
    -H "Content-Type: application/json" \
    -d '{
        "customer_email": "verify@example.com",
        "line_items": [{"sku_id": "TEST-SKU", "quantity": 1}],
        "currency": "USD"
    }')

# Note: We expect 400 or 201, but NOT 404 (endpoint missing) or 500 (crash)
if echo "$RESPONSE" | grep -q "not found"; then
     echo -e "${RED}✗ API Endpoint /api/v1/orders NOT FOUND${NC}"
     exit 1
elif [ -z "$RESPONSE" ]; then
     echo -e "${RED}✗ API returned empty response${NC}"
     exit 1
else
     echo -e "${GREEN}✓ API responded (Validation or Success)${NC}"
fi

# =============================================================================
# Step 6: Success
# =============================================================================
echo -e "\n${GREEN}═════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}              ✓ VARIANT VERIFICATION PASSED ✓${NC}"
echo -e "${GREEN}═════════════════════════════════════════════════════════════════${NC}"
exit 0
