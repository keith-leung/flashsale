#!/bin/bash
# Variant X Verification Script
# This is NOT a SACRED verification - only Variant Y is SACRED
# This script verifies Variant X functionality for manual testing

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════"
echo "              VARIANT X VERIFICATION"
echo "         Redis Atomic Counters Implementation"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Step 1: Check if services are running
echo -e "${YELLOW}[Step 1/7] Checking Variant X services...${NC}"
if docker compose ps | grep -q "flash-mariadb-x"; then
    echo -e "${GREEN}✓ Services are running${NC}"
else
    echo -e "${YELLOW}⚠ Services not running, starting them...${NC}"
    docker compose up -d
    echo "Waiting 35 seconds for services to initialize..."
    sleep 35
fi

# Check container status
echo -e "${BLUE}Container Status:${NC}"
for container in flash-mariadb-x flash-redis-x flash-python-x flash-java-x flash-csharp-x flash-nginx-x; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        uptime=$(docker ps --format '{{.Names}} {{.Status}}' | grep "^${container}" | sed 's/.*Up //')
        echo -e "${GREEN}  ✓ ${container}: Up ${uptime}${NC}"
    else
        echo -e "${RED}  ✗ ${container}: Not running${NC}"
        exit 1
    fi
done

# Step 2: Health checks
echo ""
echo -e "${YELLOW}[Step 2/7] Running health checks...${NC}"

# Python
if curl -s http://localhost:30011/health | grep -q "200 OK"; then
    echo -e "${GREEN}✓ Python health OK (port 30011)${NC}"
else
    echo -e "${RED}✗ Python health FAILED${NC}"
    exit 1
fi

# Java
if curl -s http://localhost:8016/health | grep -q "200 OK"; then
    echo -e "${GREEN}✓ Java health OK (port 8016)${NC}"
else
    echo -e "${RED}✗ Java health FAILED${NC}"
    exit 1
fi

# C#
if curl -s http://localhost:30012/health | grep -q "200 OK"; then
    echo -e "${GREEN}✓ C# health OK (port 30012)${NC}"
else
    echo -e "${RED}✗ C# health FAILED${NC}"
    exit 1
fi

# Step 3: Database connectivity
echo ""
echo -e "${YELLOW}[Step 3/7] Testing database connectivity...${NC}"
if docker exec flash-mariadb-x mysqladmin ping -h localhost -usyracuse -pOrange_315_Forever! 2>&1 | grep -q "alive"; then
    echo -e "${GREEN}✓ MariaDB connection OK (port 3312)${NC}"
else
    echo -e "${RED}✗ MariaDB connection FAILED${NC}"
    exit 1
fi

# Step 4: Redis connectivity
echo ""
echo -e "${YELLOW}[Step 4/7] Testing Redis connectivity...${NC}"
if docker exec flash-redis-x redis-cli ping 2>&1 | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis connection OK${NC}"
else
    echo -e "${RED}✗ Redis connection FAILED${NC}"
    exit 1
fi

# Step 5: Check if database schema exists
echo ""
echo -e "${YELLOW}[Step 5/7] Checking database schema...${NC}"
TABLES=$(docker exec flash-mariadb-x mysql -usyracuse -pOrange_315_Forever! -D orange315 -e "SHOW TABLES;" 2>/dev/null | grep -c "orders" || echo "0")
if [ "$TABLES" -gt 0 ]; then
    echo -e "${GREEN}✓ Database schema exists${NC}"
else
    echo -e "${YELLOW}⚠ Database schema not found${NC}"
    echo "  You may need to run migrations:"
    echo "  docker exec flash-mariadb-x mysql -usyracuse -pOrange_315_Forever! orange315 < variant-x/migrations/001_add_flash_sale_campaigns.sql"
fi

# Step 6: Test basic order creation (Variant Y path)
echo ""
echo -e "${YELLOW}[Step 6/7] Testing basic functionality...${NC}"
echo -e "${BLUE}Note: Full order creation tests require SKU data in database${NC}"
echo -e "${BLUE}This verification confirms services are running and responsive${NC}"

# Step 7: Nginx connectivity
echo ""
echo -e "${YELLOW}[Step 7/7] Testing Nginx load balancer...${NC}"
if curl -sk https://localhost:8445/health 2>&1 | grep -q "200 OK"; then
    echo -e "${GREEN}✓ Nginx HTTPS OK (port 8445)${NC}"
else
    echo -e "${YELLOW}⚠ Nginx health check (may need SSL cert setup)${NC}"
fi

# Summary
echo ""
echo -e "${BOLD}${GREEN}"
echo "═══════════════════════════════════════════════════════════════"
echo "           ✓ VARIANT X VERIFICATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Variant X is ready for testing and development${NC}"
echo ""
echo -e "${BLUE}Service Endpoints:${NC}"
echo "  Python:  http://localhost:30011"
echo "  Java:    http://localhost:8016"
echo "  C#:      http://localhost:30012"
echo "  Nginx:   https://localhost:8445"
echo "  MariaDB: localhost:3312"
echo ""
echo -e "${BLUE}Key Differences from Variant Y:${NC}"
echo "  • Uses Redis atomic counters (DECRBY) for flash sales"
echo "  • Zero database queries during flash sale orders"
echo "  • Async order persistence via Redis Streams"
echo "  • Intelligent routing (same endpoint, automatic optimization)"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Load flash sale campaigns to database"
echo "  2. Load flash sales to Redis: docker exec flash-python-x python /app/load_flash_sales_to_redis.py"
echo "  3. Run benchmarks to compare with Variant Y"
echo "  4. Test intelligent routing with mixed workloads"
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  Status:      docker compose ps"
echo "  Logs:        docker compose logs -f [service-name]"
echo "  Stop:        docker compose down"
echo "  Restart:     docker compose restart [service-name]"
