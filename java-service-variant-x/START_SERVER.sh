#!/bin/bash
# Start Java Spring Boot service

cd "$(dirname "$0")"

echo "=========================================="
echo "Starting Java Flash Sale Service"
echo "=========================================="
echo ""
echo "Port: 8081"
echo "Database: 127.0.0.1:3306/orange315"
echo ""

# Check if port 8081 is already in use
if lsof -Pi :8081 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "WARNING: Port 8081 is already in use"
    echo "Stop the existing service first or use a different port"
    exit 1
fi

# Set instance ID for Snowflake ID generator (default: 1)
export APP_INSTANCE_ID=${INSTANCE_ID:-1}

echo "Starting with INSTANCE_ID=$APP_INSTANCE_ID"
echo ""

# Start the service
mvn spring-boot:run
