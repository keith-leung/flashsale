#!/bin/bash
# Adaptive Health Benchmark for Variant Z
# Tests health endpoint with increasing concurrency until latency exceeds 100ms

set -e

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:8080}"
HEALTH_ENDPOINT="/health"
MAX_LATENCY_MS=100
MAX_CONCURRENCY=1000
WARMUP_DURATION=5
TEST_DURATION=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Adaptive Health Benchmark - Variant Z"
echo "=========================================="
echo "Service URL: $SERVICE_URL"
echo "Max Latency: ${MAX_LATENCY_MS}ms"
echo ""

# Function to test health endpoint
test_health() {
    local concurrency=$1
    local duration=$2
    local method=$3
    
    echo -n "Testing $method at concurrency=$concurrency... "
    
    # Run wrk and capture output
    local output
    output=$(wrk -t$concurrency -c$concurrency -d${duration}s --latency \
        -s <(cat <<EOF
            local method = "$method"
            request = function()
                return wrk.format(method, path)
            end
EOF
) "$SERVICE_URL$HEALTH_ENDPOINT" 2>&1)
    
    # Extract latency (average in microseconds)
    local latency_us=$(echo "$output" | grep "Latency" | awk '{print $2}' | sed 's/us//')
    local latency_ms=$(echo "scale=2; $latency_us / 1000" | bc)
    
    # Extract throughput (requests per second)
    local throughput=$(echo "$output" | grep "Requests/sec" | awk '{print $2}')
    
    echo "Latency: ${latency_ms}ms, Throughput: ${throughput} req/s"
    
    # Return values
    echo "$latency_ms|$throughput"
}

# Function to run adaptive test
run_adaptive_test() {
    local method=$1
    local concurrency=1
    local max_throughput=0
    local max_latency=0
    local optimal_concurrency=1
    
    echo ""
    echo "----------------------------------------"
    echo "Testing $method method"
    echo "----------------------------------------"
    
    while [ $concurrency -le $MAX_CONCURRENCY ]; do
        result=$(test_health $concurrency $TEST_DURATION "$method")
        latency_ms=$(echo "$result" | cut -d'|' -f1)
        throughput=$(echo "$result" | cut -d'|' -f2)
        
        # Check if latency exceeds threshold
        if (( $(echo "$latency_ms > $MAX_LATENCY_MS" | bc -l) )); then
            echo -e "${YELLOW}Latency ${latency_ms}ms exceeds threshold ${MAX_LATENCY_MS}ms${NC}"
            break
        fi
        
        # Update max throughput
        if (( $(echo "$throughput > $max_throughput" | bc -l) )); then
            max_throughput=$throughput
            max_latency=$latency_ms
            optimal_concurrency=$concurrency
        fi
        
        # Double concurrency for next iteration
        concurrency=$((concurrency * 2))
    done
    
    echo ""
    echo -e "${GREEN}Results for $method:${NC}"
    echo "  Max Throughput: $max_throughput req/s"
    echo "  Latency at Max: $max_latency ms"
    echo "  Optimal Concurrency: $optimal_concurrency"
    
    # Return results
    echo "$max_throughput|$max_latency|$optimal_concurrency"
}

# Warmup
echo "Warming up service for ${WARMUP_DURATION}s..."
wrk -t4 -c10 -d${WARMUP_DURATION}s "$SERVICE_URL$HEALTH_ENDPOINT" > /dev/null 2>&1
echo "Warmup complete"
echo ""

# Test GET method
get_results=$(run_adaptive_test "GET")
get_throughput=$(echo "$get_results" | cut -d'|' -f1)
get_latency=$(echo "$get_results" | cut -d'|' -f2)
get_concurrency=$(echo "$get_results" | cut -d'|' -f3)

# Test HEAD method
head_results=$(run_adaptive_test "HEAD")
head_throughput=$(echo "$head_results" | cut -d'|' -f1)
head_latency=$(echo "$head_results" | cut -d'|' -f2)
head_concurrency=$(echo "$head_results" | cut -d'|' -f3)

# Final results
echo ""
echo "=========================================="
echo "Adaptive Health Benchmark Results"
echo "=========================================="
echo ""
echo "GET Method:"
echo "  Max Throughput: $get_throughput req/s"
echo "  Latency at Max: $get_latency ms"
echo "  Concurrency: $get_concurrency"
echo ""
echo "HEAD Method:"
echo "  Max Throughput: $head_throughput req/s"
echo "  Latency at Max: $head_latency ms"
echo "  Concurrency: $head_concurrency"
echo ""

# Determine overall result
overall_throughput=$get_throughput
overall_latency=$get_latency

if (( $(echo "$head_throughput > $get_throughput" | bc -l) )); then
    overall_throughput=$head_throughput
    overall_latency=$head_latency
fi

echo "Overall:"
echo "  Max Throughput: $overall_throughput req/s"
echo "  Latency at Max: $overall_latency ms"
echo ""

# Check if benchmark passed
if (( $(echo "$overall_latency < $MAX_LATENCY_MS" | bc -l) )); then
    echo -e "${GREEN}✓ Health benchmark PASSED${NC}"
    echo "  Service is healthy and performing well"
    exit 0
else
    echo -e "${RED}✗ Health benchmark FAILED${NC}"
    echo "  Latency exceeds threshold at max throughput"
    exit 1
fi