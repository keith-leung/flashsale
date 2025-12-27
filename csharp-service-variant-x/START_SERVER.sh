#!/bin/bash
# Start C# ASP.NET Core service

cd "$(dirname "$0")"

echo "=========================================="
echo "Starting C# Flash Sale Service"
echo "=========================================="
echo ""
echo "Port: 8082"
echo "Database: 127.0.0.1:3306/orange315"
echo ""

# Check if port 8082 is already in use
if lsof -Pi :8082 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "WARNING: Port 8082 is already in use"
    echo "Stop the existing service first or use a different port"
    exit 1
fi

# Set instance ID for Snowflake ID generator (default: 1)
export App__InstanceId=${INSTANCE_ID:-1}

echo "Starting with INSTANCE_ID=$App__InstanceId"
echo ""

# Start the service
dotnet run --urls "http://0.0.0.0:8082"
