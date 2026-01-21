#!/bin/bash
# Start server for Variant V Python Service

echo "Starting Variant V Python Service..."
echo "Campaign-Aware Distributed Locking + Write-Ahead Audit"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
python -m app.main
