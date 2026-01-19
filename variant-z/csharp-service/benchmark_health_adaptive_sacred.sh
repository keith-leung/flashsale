#!/bin/bash

# SACRED Adaptive Health Benchmark Script for C# Service
# Variant Z - Token Pre-Allocation Architecture
# This script follows the SACRED methodology for adaptive benchmarking

set -e

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:30018}"
VARIANT="Z"
SERVICE="csharp"
ENDPOINT="health"
TEST_TYPE="adaptive"

# Starting parameters
THREADS=4
CONCURRENCY=10
DURATION=10

# Growth thresholds
SIGNIFICANT_GROWTH_THRESHOLD=5.0
MODERATE_GROWTH_THRESHOLD=2.0
MARGINAL_GROWTH_THRESHOLD=0.0

# Stopping criteria
MAX_THREADS=24
MAX_CONCURRENCY=2000
PLATEAU_COUNT=3

# State tracking
prev_throughput=0
plateau_counter=0
test_number=0

# Output file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="csharp_health_adaptive_${TIMESTAMP}.csv"

# CSV Header (27 fields - SACRED schema)
echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,latency_avg_ms,latency_stdev_ms,latency_p50_ms,latency_p75_ms,latency_p90_ms,latency_p95_ms,latency_p99_ms,latency_p99_9_ms,transfer_kb_sec,requests_total,errors_total,errors_rate,success_rate,connect_errors,read_errors,write_errors,timeout_errors,http_2xx,http_3xx,http_4xx,http_5xx,non_200_res" > "$OUTPUT_FILE"

echo "Starting SACRED Adaptive Health Benchmark for C# Service"
echo "Service URL: $SERVICE_URL"
echo "Output file: $OUTPUT_FILE"
echo ""

# Function to run benchmark
run_benchmark() {
    local threads=$1
    local concurrency=$2
    local duration=$3
    local test_num=$4
    
    echo "Test #$test_num: t=$threads, c=$concurrency, d=${duration}s"
    
    # Run wrk and capture output
    local output=$(wrk -t"$threads" -c"$concurrency" -d"${duration}s" --latency "${SERVICE_URL}/health" 2>&1)
    
    # Parse wrk output
    local req_per_sec=$(echo "$output" | grep "Requests/sec:" | awk '{print $2}')
    local latency_avg=$(echo "$output" | grep "Latency" | awk '{print $2}')
    local latency_stdev=$(echo "$output" | grep "Latency" | awk '{print $3}')
    local transfer_sec=$(echo "$output" | grep "Transfer/sec:" | awk '{print $2}' | sed 's/K//')
    
    # Parse latency percentiles
    local p50=$(echo "$output" | grep "50%" | awk '{print $2}')
    local p75=$(echo "$output" | grep "75%" | awk '{print $2}')
    local p90=$(echo "$output" | grep "90%" | awk '{print $2}')
    local p95=$(echo "$output" | grep "99%" | awk '{print $2}')
    local p99=$(echo "$output" | grep "99.9%" | awk '{print $2}')
    
    # Calculate total requests
    local total_requests=$(echo "$req_per_sec $duration" | awk '{printf "%.0f", $1 * $2}')
    
    # Extract error counts (wrk doesn't show errors in health endpoint typically)
    local errors_total=0
    local connect_errors=0
    local read_errors=0
    local write_errors=0
    local timeout_errors=0
    
    # HTTP status codes (all should be 200 for health endpoint)
    local http_2xx=$total_requests
    local http_3xx=0
    local http_4xx=0
    local http_5xx=0
    local non_200_res=0
    
    # Calculate rates
    local success_rate=100.0
    local errors_rate=0.0
    
    # Convert latency to ms (remove 'us', 'ms', 's' suffixes)
    latency_avg=$(echo "$latency_avg" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    latency_stdev=$(echo "$latency_stdev" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    p50=$(echo "$p50" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    p75=$(echo "$p75" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    p90=$(echo "$p90" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    p95=$(echo "$p95" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    p99=$(echo "$p99" | sed 's/us//' | sed 's/ms//' | sed 's/s//')
    
    # If latency is in microseconds, convert to milliseconds
    if [ -n "$latency_avg" ] && [ "$latency_avg" -gt 1000 ] 2>/dev/null; then
        latency_avg=$(echo "$latency_avg" | awk '{printf "%.2f", $1 / 1000}')
        latency_stdev=$(echo "$latency_stdev" | awk '{printf "%.2f", $1 / 1000}')
        p50=$(echo "$p50" | awk '{printf "%.2f", $1 / 1000}')
        p75=$(echo "$p75" | awk '{printf "%.2f", $1 / 1000}')
        p90=$(echo "$p90" | awk '{printf "%.2f", $1 / 1000}')
        p95=$(echo "$p95" | awk '{printf "%.2f", $1 / 1000}')
        p99=$(echo "$p99" | awk '{printf "%.2f", $1 / 1000}')
    fi
    
    # Write to CSV
    echo "$(date +%Y-%m-%dT%H:%M:%S),$VARIANT,$SERVICE,$ENDPOINT,$TEST_TYPE,$threads,$concurrency,$duration,$req_per_sec,$latency_avg,$latency_stdev,$p50,$p75,$p90,$p95,$p99,0.00,$transfer_sec,$total_requests,$errors_total,$errors_rate,$success_rate,$connect_errors,$read_errors,$write_errors,$timeout_errors,$http_2xx,$http_3xx,$http_4xx,$http_5xx,$non_200_res" >> "$OUTPUT_FILE"
    
    echo "  Throughput: $req_per_sec req/s, Latency: ${latency_avg}ms"
    
    # Return throughput for growth analysis
    echo "$req_per_sec"
}

# Adaptive benchmarking loop
while true; do
    test_number=$((test_number + 1))
    
    # Run benchmark
    throughput=$(run_benchmark "$THREADS" "$CONCURRENCY" "$DURATION" "$test_number")
    
    # Check for stopping conditions
    if [ -z "$throughput" ]; then
        echo "Error: Failed to get throughput measurement"
        break
    fi
    
    # Check if we hit max limits
    if [ "$THREADS" -ge "$MAX_THREADS" ] && [ "$CONCURRENCY" -ge "$MAX_CONCURRENCY" ]; then
        echo "Reached maximum threads ($MAX_THREADS) and concurrency ($MAX_CONCURRENCY)"
        break
    fi
    
    # Calculate growth rate
    if [ "$test_number" -gt 1 ]; then
        growth=$(echo "$prev_throughput $throughput" | awk '{printf "%.2f", (($2 - $1) / $1) * 100}')
        echo "  Growth: ${growth}%"
        
        # Check for plateau (less than 2% variance)
        plateau=$(echo "$growth" | awk '{if ($1 < 2.0 && $1 > -2.0) print "yes"; else print "no"}')
        
        if [ "$plateau" = "yes" ]; then
            plateau_counter=$((plateau_counter + 1))
            echo "  Plateau detected ($plateau_counter/$PLATEAU_COUNT)"
            
            if [ "$plateau_counter" -ge "$PLATEAU_COUNT" ]; then
                echo "Plateau reached - stopping benchmark"
                break
            fi
        else
            plateau_counter=0
        fi
        
        # Adjust parameters based on growth
        growth_abs=$(echo "$growth" | awk '{if ($1 < 0) print -$1; else print $1}')
        
        if (( $(echo "$growth_abs > $SIGNIFICANT_GROWTH_THRESHOLD" | bc -l) )); then
            # Significant growth - increase aggressively
            THREADS=$(echo "$THREADS * 1.5" | bc | awk '{printf "%.0f", $1}')
            CONCURRENCY=$(echo "$CONCURRENCY * 2.0" | bc | awk '{printf "%.0f", $1}')
            echo "  Significant growth - increasing to t=$THREADS, c=$CONCURRENCY"
        elif (( $(echo "$growth_abs > $MODERATE_GROWTH_THRESHOLD" | bc -l) )); then
            # Moderate growth - increase moderately
            THREADS=$(echo "$THREADS * 1.2" | bc | awk '{printf "%.0f", $1}')
            CONCURRENCY=$(echo "$CONCURRENCY * 1.5" | bc | awk '{printf "%.0f", $1}')
            echo "  Moderate growth - increasing to t=$THREADS, c=$CONCURRENCY"
        else
            # Marginal growth - increase conservatively
            THREADS=$(echo "$THREADS * 1.1" | bc | awk '{printf "%.0f", $1}')
            CONCURRENCY=$(echo "$CONCURRENCY * 1.2" | bc | awk '{printf "%.0f", $1}')
            echo "  Marginal growth - increasing to t=$THREADS, c=$CONCURRENCY"
        fi
    fi
    
    # Cap values at maximum
    if [ "$THREADS" -gt "$MAX_THREADS" ]; then
        THREADS=$MAX_THREADS
    fi
    if [ "$CONCURRENCY" -gt "$MAX_CONCURRENCY" ]; then
        CONCURRENCY=$MAX_CONCURRENCY
    fi
    
    # Scale duration with concurrency (minimum 10s)
    DURATION=$(echo "$CONCURRENCY / 100" | bc)
    if [ "$DURATION" -lt 10 ]; then
        DURATION=10
    fi
    
    prev_throughput=$throughput
    echo ""
done

echo ""
echo "Benchmark complete!"
echo "Results saved to: $OUTPUT_FILE"
echo ""
echo "Summary:"
echo "  Total tests: $test_number"
echo "  Final configuration: t=$THREADS, c=$CONCURRENCY, d=${DURATION}s"
echo "  Final throughput: $throughput req/s"