#!/bin/bash
# Start Java service for Variant V

echo "Building and starting Java service for Variant V..."

cd "$(dirname "$0")"

# Start the service
./mvnw spring-boot:run \
  -Dspring-boot.run.arguments="--server.port=8018" &

SERVICE_PID=$!

echo "Java service started with PID: $SERVICE_PID"
echo "Waiting for service to initialize..."
sleep 10

# Check if service is running
if curl -s http://localhost:8018/health > /dev/null; then
  echo "✓ Java service started successfully on port 8018"
else
  echo "✗ Failed to start Java service"
  kill $SERVICE_PID 2>/dev/null
  exit 1
fi

trap "kill $SERVICE_PID" EXIT
wait $SERVICE_PID
