#!/bin/bash
# Setup and test Variant V Python Service

echo "Setting up Variant V Python Service..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    /usr/bin/python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Test health endpoint
echo ""
echo "Testing health endpoint..."

# Start in background
python -m app.main > /tmp/variant_v_test.log 2>&1 &
PID=$!

# Wait for startup
sleep 3

# Test
curl -s http://localhost:8000/health
STATUS=$?

# Cleanup
kill $PID 2>/dev/null

# Check result
if [ $STATUS -eq 0 ]; then
    echo ""
    echo "✓ Health endpoint working!"
    exit 0
else
    echo ""
    echo "✗ Health endpoint test failed"
    echo "Server logs:"
    cat /tmp/variant_v_test.log
    exit 1
fi
