#!/bin/bash
# =============================================================================
# Variant Y Status Check - Quick Health Verification
# =============================================================================
# This script quickly verifies that Variant Y is ready for benchmarking.
# Run this before starting any development or testing.
#
# Usage: bash check_variant_y.sh
# =============================================================================

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Variant Y Status Check${NC}"
echo -e "${YELLOW}========================================${NC}"

# Check containers
echo -e "\n${YELLOW}[1/4] Container Status${NC}"
CONTAINERS=("flash-mariadb" "flash-redis" "flash-python" "flash-java" "flash-csharp" "flash-nginx")
ALL_OK=true

for container in "${CONTAINERS[@]}"; do
    STATUS=$(podman ps --filter "name=^${container}$" --format "{{.Status}}" 2>/dev/null)
    if [ -n "$STATUS" ]; then
        echo -e "${GREEN}✓ ${container}: ${STATUS}${NC}"
    else
        echo -e "${RED}✗ ${container}: NOT RUNNING${NC}"
        ALL_OK=false
    fi
done

# Check ports
echo -e "\n${YELLOW}[2/4] Port Availability${NC}"
PORTS=("3307:MariaDB" "8000:Python" "8081:Java" "8082:C#" "8443:Nginx")
for port_info in "${PORTS[@]}"; do
    PORT="${port_info%%:*}"
    NAME="${port_info##*:}"
    if netstat -tuln 2>/dev/null | grep -q ":${PORT} "; then
        echo -e "${GREEN}✓ Port ${PORT} (${NAME}) is listening${NC}"
    else
        echo -e "${RED}✗ Port ${PORT} (${NAME}) is NOT listening${NC}"
        ALL_OK=false
    fi
done

# Check HTTP health
echo -e "\n${YELLOW}[3/4] HTTP Health Endpoints${NC}"

# Python
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Python health check passed${NC}"
else
    echo -e "${RED}✗ Python health check failed${NC}"
    ALL_OK=false
fi

# Java
if curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Java health check passed${NC}"
else
    echo -e "${RED}✗ Java health check failed${NC}"
    ALL_OK=false
fi

# C#
if curl -sf http://localhost:8082/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ C# health check passed${NC}"
else
    echo -e "${RED}✗ C# health check failed${NC}"
    ALL_OK=false
fi

# Check database
echo -e "\n${YELLOW}[4/4] Database Connectivity${NC}"
DB_CHECK=$(podman exec flash-mariadb mysql -usyracuse -pOrange_315_Forever! -e "SELECT 1" orange315 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ MariaDB connection successful${NC}"
    echo -e "${GREEN}  Database: orange315${NC}"
    echo -e "${GREEN}  User: syracuse${NC}"
else
    echo -e "${RED}✗ MariaDB connection failed${NC}"
    ALL_OK=false
fi

# Summary
echo -e "\n${YELLOW}========================================${NC}"
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ Variant Y is READY${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "You can now:"
    echo "  • Run benchmarks: bash run_4step_benchmark.sh"
    echo "  • Run unit tests: podman exec flash-python python -m pytest"
    echo "  • Connect DataGrip:"
    echo "      Host: localhost"
    echo "      Port: 3307"
    echo "      Database: orange315"
    echo "      User: syracuse"
    echo "      Password: Orange_315_Forever!"
    exit 0
else
    echo -e "${RED}✗ Variant Y has issues${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo "To fix, run: podman-compose up -d"
    echo "Then wait 30s and run this script again."
    exit 1
fi
