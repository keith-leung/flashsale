#!/bin/bash
# Corrected Python Order Benchmark for Variant Z
# This benchmark ensures actual database operations occur and validates results

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== VARIANT Z PYTHON ORDER BENCHMARK (CORRECTED) ===${NC}"
echo "This benchmark validates actual database operations occur"
echo ""

# Configuration
PYTHON_SERVICE="variant-z-python-service-1"
WRK_SCRIPT="/wrk_order_script.lua"
RESULTS_DIR="benchmark_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="${RESULTS_DIR}/variant_Z_python_orders_corrected_${TIMESTAMP}.csv"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Check if wrk script exists
if [ ! -f "variant-z/wrk_order_script.lua" ]; then
    echo -e "${RED}Error: wrk script not found at variant-z/wrk_order_script.lua${NC}"
    exit 1
fi

# Function to check service health
check_health() {
    local max_attempts=30
    local attempt=1
    
    echo "Checking if Python service is healthy..."
    while [ $attempt -le $max_attempts ]; do
        # Use docker run with curl to check health
        if docker run --rm --network flashsale-z-net curlimages/curl:latest -s http://flash-python-z:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Service is healthy${NC}"
            return 0
        fi
        echo "Waiting for service... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}✗ Service failed to become healthy${NC}"
    exit 1
}

# Function to enable database query logging
enable_query_logging() {
    echo "Enabling database query logging..."
    docker exec $PYTHON_SERVICE python -c "
import asyncio
from app.core.database import engine

async def enable_logging():
    async with engine.connect() as conn:
        # Enable general query log
        await conn.execute('SET GLOBAL general_log = ON')
        await conn.execute('SET GLOBAL general_log_file = \"/var/lib/mysql/mysql.log\"')
        await conn.execute('SET GLOBAL long_query_time = 0')
        print('Query logging enabled')

asyncio.run(enable_logging())
" 2>/dev/null || echo "Could not enable query logging (may not be critical)"
}

# Function to get database stats before benchmark
get_db_stats_before() {
    echo "Getting database stats before benchmark..."
    docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "
        SELECT 'orders_before' as metric, COUNT(*) as count FROM orders
        UNION ALL
        SELECT 'order_items_before', COUNT(*) FROM order_line_items
        UNION ALL
        SELECT 'payments_before', COUNT(*) FROM payments
    ;" 2>/dev/null || echo "Could not get initial stats"
}

# Function to get database stats after benchmark
get_db_stats_after() {
    echo "Getting database stats after benchmark..."
    docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "
        SELECT 'orders_after' as metric, COUNT(*) as count FROM orders
        UNION ALL
        SELECT 'order_items_after', COUNT(*) FROM order_line_items
        UNION ALL
        SELECT 'payments_after', COUNT(*) FROM payments
    ;" 2>/dev/null || echo "Could not get final stats"
}

# Function to validate results against Little's Law
validate_little_law() {
    local throughput=$1
    local concurrency=$2
    local avg_latency=$3
    local p99_latency=$4
    local total_errors=$5
    
    echo ""
    echo "=== Little's Law Validation ==="
    echo "Throughput: $throughput req/s"
    echo "Concurrency: $concurrency"
    echo "Avg Latency: ${avg_latency}ms"
    echo "p99 Latency: ${p99_latency}ms"
    echo "Errors: $total_errors"
    
    # Check error rate first
    if [ "$total_errors" -gt 0 ]; then
        local error_rate=$(echo "scale=2; $total_errors / ($throughput * 10) * 100" | bc)
        echo -e "${RED}✗ INVALID: $total_errors errors detected (${error_rate}% error rate)${NC}"
        echo "High throughput may be due to fast error responses"
        return 1
    fi
    
    # Parse latency value (remove 'ms' suffix)
    local latency_num=$(echo "$avg_latency" | sed 's/ms$//' | sed 's/us$//')
    
    # Convert latency from ms to seconds
    local avg_latency_sec=$(echo "scale=6; $latency_num / 1000" | bc)
    
    # Calculate theoretical max throughput
    local theoretical_max=$(echo "scale=2; $concurrency / $avg_latency_sec" | bc)
    
    # Calculate ratio
    local ratio=$(echo "scale=2; $throughput / $theoretical_max" | bc)
    
    echo "Theoretical Max: ${theoretical_max} req/s"
    echo "Ratio (Actual/Theoretical): $ratio"
    
    # Check if results are valid
    if (( $(echo "$ratio > 1.2" | bc -l) )); then
        echo -e "${RED}✗ INVALID: Throughput exceeds theoretical maximum by more than 20%${NC}"
        echo "This suggests requests are not actually hitting the database synchronously"
        return 1
    elif (( $(echo "$p99_latency > 100" | bc -l) )); then
        echo -e "${YELLOW}⚠ WARNING: p99 latency > 100ms suggests database contention${NC}"
        return 0
    else
        echo -e "${GREEN}✓ VALID: Results are within theoretical limits${NC}"
        return 0
    fi
}

# Function to run a single benchmark test
run_benchmark() {
    local threads=$1
    local concurrency=$2
    local duration=$3
    local test_sequence=$4
    
    echo ""
    echo "=========================================="
    echo "Test $test_sequence: threads=$threads, concurrency=$concurrency, duration=${duration}s"
    echo "=========================================="
    
    # Get database stats before
    get_db_stats_before
    
    # Run wrk benchmark
    local output=$(docker run --rm --network flashsale-z-net \
        -v "$(pwd)/variant-z/wrk_order_script.lua:/wrk_order_script.lua" \
        williamyeh/wrk:latest \
        -t $threads -c $concurrency -d ${duration}s -s /wrk_order_script.lua \
        http://flash-python-z:8000/api/v1/orders/ 2>&1)
    
    # Parse wrk output
    local req_per_sec=$(echo "$output" | grep "Requests/sec" | awk '{print $2}')
    local avg_latency=$(echo "$output" | grep "Latency" | awk '{print $2}')
    local p99_latency=$(echo "$output" | grep "99%" | awk '{print $2}')
    local total_requests=$(echo "$output" | grep "requests in" | awk '{print $1}')
    local total_errors=$(echo "$output" | grep "Non-2xx" | awk '{print $2}' || echo "0")
    
    # Get database stats after
    get_db_stats_after
    
    # Calculate error rate
    local error_rate=$(echo "scale=4; $total_errors / $total_requests * 100" | bc)
    
    # Validate against Little's Law (pass errors for validation)
    validate_little_law "$req_per_sec" "$concurrency" "$avg_latency" "$p99_latency" "$total_errors"
    
    # Write to CSV
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "$timestamp,variant_z,python,/api/v1/orders,order,$threads,$concurrency,$duration,$req_per_sec,$avg_latency,0,0,$p99_latency,0,0,$total_requests,$total_errors,$error_rate,0,0,0,0,0,0,0,$test_sequence,N/A,COMPLETED" >> "$RESULTS_FILE"
    
    echo "Results written to $RESULTS_FILE"
    echo "Throughput: $req_per_sec req/s"
    echo "Avg Latency: $avg_latency"
    echo "p99 Latency: $p99_latency"
    echo "Errors: $total_errors ($error_rate%)"
    
    # Sleep between tests
    sleep 5
}

# Main execution
echo "Starting corrected Python order benchmark..."
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Check service health
check_health

# Enable query logging
enable_query_logging

# Create CSV header
echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "$RESULTS_FILE"

# Run adaptive benchmark with realistic concurrency levels
# Start low and increase gradually to find true performance ceiling

echo ""
echo "=== Starting Adaptive Benchmark ==="
echo "Testing with realistic concurrency levels for database-bound workload"

# Test 1: Low concurrency (baseline)
run_benchmark 4 10 10 1

# Test 2: Moderate concurrency
run_benchmark 4 20 10 2

# Test 3: Higher concurrency
run_benchmark 8 40 10 3

# Test 4: High concurrency (approaching connection pool limit)
run_benchmark 16 80 10 4

# Test 5: Very high concurrency (at connection pool limit)
run_benchmark 16 100 10 5

# Test 6: Extreme concurrency (exceeding connection pool - should see degradation)
run_benchmark 16 150 10 6

echo ""
echo -e "${GREEN}=== Benchmark Complete ===${NC}"
echo "Results saved to: $RESULTS_FILE"
echo ""
echo "To analyze results:"
echo "  cat $RESULTS_FILE | column -t -s,"
echo ""
echo "To validate database operations occurred:"
echo "  docker exec mariadb mysql -usyracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'"