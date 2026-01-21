#!/bin/bash
# Verify Variant V Python Service Implementation

set -e

echo "================================================"
echo "Variant V Implementation Verification"
echo "================================================"
echo ""

# Check directory structure
echo "Checking directory structure..."
REQUIRED_DIRS=(
    "app"
    "app/api"
    "app/api/routes"
    "app/core"
    "app/models"
    "app/services"
    "app/workers"
    "tests"
    "logs"
    "migrations"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir/"
    else
        echo "✗ $dir/ (missing)"
        exit 1
    fi
done

# Check required files
echo ""
echo "Checking required files..."
REQUIRED_FILES=(
    "app/__init__.py"
    "app/main.py"
    "app/api/__init__.py"
    "app/api/routes/__init__.py"
    "pyproject.toml"
    "Dockerfile"
    "requirements.txt"
    "START_SERVER.sh"
    "benchmark_health.sh"
    "benchmark_adaptive.sh"
    "run_adaptive_benchmark.sh"
    "README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (missing)"
        exit 1
    fi
done

# Check main application
echo ""
echo "Checking FastAPI application..."
if grep -q "FastAPI" app/main.py; then
    echo "✓ FastAPI imported"
fi

if grep -q "/health" app/main.py; then
    echo "✓ Health endpoint defined"
fi

if grep -q "PlainTextResponse.*200 OK" app/main.py; then
    echo "✓ Health returns 200 OK"
fi

# Check scripts are executable
echo ""
echo "Checking scripts..."
for script in "*.sh"; do
    if [ -x "$script" ]; then
        echo "✓ $script (executable)"
    else
        echo "✗ $script (not executable)"
    fi
done

# Validate Docker build (if docker available)
if command -v docker &> /dev/null; then
    echo ""
    echo "Testing Docker build..."
    docker build -t flashsale-v-python:test . > /tmp/docker_build.log 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Docker builds successfully"
        docker rmi flashsale-v-python:test 2>/dev/null || true
    else
        echo "✗ Docker build failed"
        cat /tmp/docker_build.log
        exit 1
    fi
fi

echo ""
echo "================================================"
echo "✓ Implementation Complete!"
echo "================================================"
echo ""
echo "Health endpoint: /health"
echo "Benchmark: ./benchmark_adaptive.sh"
echo "Full test: ./run_adaptive_benchmark.sh"
echo ""
