#!/bin/bash
# =============================================================================
# Variant Z Python Service - Adaptive Health Benchmark (SACRED Methodology)
# =============================================================================
# 
# This script implements the SACRED VERIFICATION adaptive plateau detection
# algorithm for testing the /health endpoint.
#
# CRITICAL: This script MUST use the EXACT same methodology as all variants
# to enable fair performance comparison.
#
# SACRED Methodology:
# - Starting: t=4, c=10
# - Growth analysis: >5% (significant), 2-5% (moderate), 0-2% (marginal)
# - Plateau: <2% variance across 3 consecutive tests
# - Stop: any 503, or t=24 c=2000 caps
# - CSV: 27 fields (exact SACRED schema)
#
# =============================================================================

set -e

# Configuration
SERVICE_URL="${SERVICE_URL:-http://localhost:30017}"
HEALTH_ENDPOINT="/health"
START_THREADS=4
START_CONCURRENCY=10
MAX_THREADS=24
MAX_CONCURRENCY=2000
BASE_DURATION=10

# CSV output
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
CSV_FILE="python_health_adaptive_${TIMESTAMP}.csv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize CSV header (SACRED schema)
init_csv() {
    cat > "$CSV_FILE" <<'EOF'
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
EOF
}

# Write row to CSV
write_csv_row() {
    local timestamp="$1"
    local variant="$2"
    local service="$3"
    local endpoint="$4"
    local test_type="$5"
    local threads="$6"
    local concurrency="$7"
    local duration_s="$8"
    local req_per_sec="$9"
    local avg_latency_ms="$10"
    local p50_latency_ms="$11"
    local p90_latency_ms="$12"
    local p99_latency_ms="$13"
    local max_latency_ms="$14"
    local stdev_latency_ms="$15"
    local total_requests="$16"
    local total_errors="$17"
    local error_rate_pct="$18"
    local non_2xx_3xx="$19"
    local socket_errors_connect="$20"
    local socket_errors_read="$21"
    local socket_errors_write="$22"
    local socket_errors_timeout="$23"
    local transfer_mb="$24"
    local throughput_mb_s="$25"
    local test_sequence="$26"
    local throughput_increase_pct="$27"
    local decision="$28"
    
    echo "${timestamp},${variant},${service},${endpoint},${test_type},${threads},${concurrency},${duration_s},${req_per_sec},${avg_latency_ms},${p50_latency_ms},${p90_latency_ms},${p99_latency_ms},${max_latency_ms},${stdev_latency_ms},${total_requests},${total_errors},${error_rate_pct},${non_2xx_3xx},${socket_errors_connect},${socket_errors_read},${socket_errors_write},${socket_errors_timeout},${transfer_mb},${throughput_mb_s},${test_sequence},${throughput_increase_pct},${decision}" >> "$CSV_FILE"
}

# Run wrk and parse output
run_wrk() {
    local threads=$1
    local concurrency=$2
    local duration=$3
    local test_sequence=$4
    
    echo -e "${GREEN}Running test ${test_sequence}: t=${threads}, c=${concurrency}, d=${duration}s${NC}"
    
    # Run wrk
    local output=$(wrk -t${threads} -c${concurrency} -d${duration}s --latency "$SERVICE_URL$HEALTH_ENDPOINT" 2>&1)
    
    # Parse wrk output
    local req_per_sec=$(echo "$output" | grep "Requests/sec" | awk '{print $2}')
    local avg_latency_ms=$(echo "$output" | grep "Latency" | awk '{print $2}')
    local p50_latency_ms=$(echo "$output" | awk '/Latency/{getline; print $2}')
    local p90_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; print $2}')
    local p99_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; print $2}')
    local max_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; getline; print $2}')
    local stdev_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; getline; getline; print $2}')
    
    # Extract socket errors from wrk output
    local socket_errors_connect=$(echo "$output" | grep -i "connect" | awk '{print $1}' || echo "0")
    local socket_errors_read=$(echo "$output" | grep -i "read" | awk '{print $1}' || echo "0")
    local socket_errors_write=$(echo "$output" | grep -i "write" | awk '{print $1}' || echo "0")
    local socket_errors_timeout=$(echo "$output" | grep -i "timeout" | awk '{print $1}' || echo "0")
    
    # Check for non-2xx/3xx responses
    local total_requests=$(echo "$output" | grep "requests in" | awk '{print $1}')
    local total_errors=$((socket_errors_connect + socket_errors_read + socket_errors_write + socket_errors_timeout))
    local error_rate_pct=$(awk "BEGIN {if ($1>0) printf \"%.2f\", ($2/$1)*100; else print \"0.00\"}" <<< "$total_requests $req_per_sec")
    
    # Parse transfer stats
    local transfer_mb=$(echo "$output" | grep "Transfer/sec" | awk '{printf "%.2f", $2/1024/1024}' || echo "0.00")
    local throughput_mb_s=$(echo "$transfer_mb" | awk '{printf "%.2f", $1/$duration}')
    
    # Non-2xx/3xx count (assuming all errors are non-2xx)
    local non_2xx_3xx=$total_errors
    
    # Timestamp
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    echo "  Results: ${req_per_sec} req/s, ${avg_latency_ms}ms avg"
    
    # Return all values
    echo "$req_per_sec"
}

# Calculate throughput increase percentage
calc_increase_pct() {
    local current=$1
    local previous=$2
    
    if [ "$previous" = "0" ] || [ -z "$previous" ]; then
        echo "0.00"
    else
        awk "BEGIN {printf \"%.2f\", (($1-$2)/$2)*100}" <<< "$current $previous"
    fi
}

# Calculate plateau variance
calc_plateau_variance() {
    local count=$1
    shift
    local values=("$@")
    
    if [ $count -lt 3 ]; then
        echo "100.00"
        return
    fi
    
    # Calculate mean and standard deviation
    local sum=0
    for v in "${values[@]}"; do
        sum=$(awk "BEGIN {print $1+($2)}" <<< "$sum $v")
    done
    
    local mean=$(awk "BEGIN {print $1/$2}" <<< "$sum $count")
    
    local sq_sum=0
    for v in "${values[@]}"; do
        sq_sum=$(awk "BEGIN {print $1+($2-$3)^2}" <<< "$sq_sum $v $mean")
    done
    
    local stdev=$(awk "BEGIN {print sqrt($1/$2)}" <<< "$sq_sum $count")
    local variance=$(awk "BEGIN {if ($2>0) printf \"%.2f\", ($1/$2)*100; else print \"0.00\"}" <<< "$stdev $mean")
    
    echo "$variance"
}

# Main adaptive testing loop
adaptive_benchmark() {
    echo "=========================================="
    echo "Adaptive Health Benchmark - Variant Z Python"
    echo "=========================================="
    echo "Service URL: $SERVICE_URL"
    echo "Starting: t=$START_THREADS, c=$START_CONCURRENCY"
    echo ""
    
    init_csv
    
    local threads=$START_THREADS
    local concurrency=$START_CONCURRENCY
    local test_sequence=1
    local previous_throughput=0
    local recent_throughputs=()
    local decision="INITIAL"
    local final_decision=""
    
    while true; do
        # Calculate duration based on concurrency
        local duration=$BASE_DURATION
        if [ $concurrency -gt 500 ]; then
            duration=$((BASE_DURATION + 5))
        fi
        if [ $concurrency -gt 1000 ]; then
            duration=$((BASE_DURATION + 10))
        fi
        
        # Run test
        local throughput=$(run_wrk $threads $concurrency $duration $test_sequence)
        
        # Parse the output from run_wrk (extract values)
        local output=$(wrk -t${threads} -c${concurrency} -d${duration}s --latency "$SERVICE_URL$HEALTH_ENDPOINT" 2>&1)
        local req_per_sec=$(echo "$output" | grep "Requests/sec" | awk '{print $2}')
        local avg_latency_ms=$(echo "$output" | grep "Latency" | awk '{print $2}')
        local p50_latency_ms=$(echo "$output" | awk '/Latency/{getline; print $2}')
        local p90_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; print $2}')
        local p99_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; print $2}')
        local max_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; getline; print $2}')
        local stdev_latency_ms=$(echo "$output" | awk '/Latency/{getline; getline; getline; getline; getline; print $2}')
        local total_requests=$(echo "$output" | grep "requests in" | awk '{print $1}')
        local total_errors=$(echo "$output" | grep -Ei "(connect|read|write|timeout)" | awk '{s+=$1} END {print s}' || echo "0")
        local error_rate_pct=$(awk "BEGIN {if ($2>0) printf \"%.2f\", ($1/$2)*100; else print \"0.00\"}" <<< "$total_requests $req_per_sec")
        local transfer_mb=$(echo "$output" | grep "Transfer/sec" | awk '{printf "%.2f", $2/1024/1024}' || echo "0.00")
        local throughput_mb_s=$(awk "BEGIN {printf \"%.2f\", $1/$2}" <<< "$transfer_mb $duration")
        
        local non_2xx_3xx=$total_errors
        local socket_errors_connect=$(echo "$output" | grep -i "connect" | awk '{print $1}' || echo "0")
        local socket_errors_read=$(echo "$output" | grep -i "read" | awk '{print $1}' || echo "0")
        local socket_errors_write=$(echo "$output" | grep -i "write" | awk '{print $1}' || echo "0")
        local socket_errors_timeout=$(echo "$output" | grep -i "timeout" | awk '{print $1}' || echo "0")
        
        # Calculate throughput increase
        local throughput_increase_pct=$(calc_increase_pct $req_per_sec $previous_throughput)
        
        # Check for 503 errors
        local has_503=$(echo "$output" | grep -i "503" || echo "")
        if [ -n "$has_503" ]; then
            echo -e "${RED}503 error detected - SYSTEM_LIMIT${NC}"
            decision="SYSTEM_LIMIT"
            final_decision="SYSTEM_LIMIT"
            break
        fi
        
        # Write row to CSV
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        write_csv_row "$timestamp" "variant_z" "python" "$HEALTH_ENDPOINT" "health" \
            "$threads" "$concurrency" "$duration" "$req_per_sec" \
            "$avg_latency_ms" "$p50_latency_ms" "$p90_latency_ms" "$p99_latency_ms" \
            "$max_latency_ms" "$stdev_latency_ms" "$total_requests" "$total_errors" \
            "$error_rate_pct" "$non_2xx_3xx" "$socket_errors_connect" \
            "$socket_errors_read" "$socket_errors_write" "$socket_errors_timeout" \
            "$transfer_mb" "$throughput_mb_s" "$test_sequence" "$throughput_increase_pct" "$decision"
        
        # Store recent throughputs for plateau detection
        recent_throughputs+=("$req_per_sec")
        if [ ${#recent_throughputs[@]} -gt 3 ]; then
            recent_throughputs=("${recent_throughputs[@]: -3}")
        fi
        
        # Calculate plateau variance
        if [ ${#recent_throughputs[@]} -ge 3 ]; then
            local variance=$(calc_plateau_variance ${#recent_throughputs[@]} "${recent_throughputs[@]}")
            variance_bc=$(echo "$variance" | bc -l)
            
            if (( $(echo "$variance_bc < 2.00" | bc -l) )); then
                echo -e "${GREEN}Plateau confirmed: variance=${variance}% < 2%${NC}"
                decision="PLATEAU_CONFIRMED"
                final_decision="PLATEAU_CONFIRMED"
                break
            fi
        fi
        
        # Make decision based on growth
        if [ "$decision" != "PLATEAU_CONFIRMED" ] && [ "$decision" != "SYSTEM_LIMIT" ]; then
            local increase_bc=$(echo "$throughput_increase_pct" | bc -l)
            
            if (( $(echo "$increase_bc > 5.00" | bc -l) )); then
                echo -e "${GREEN}Significant growth: ${throughput_increase_pct}%${NC}"
                decision="SIGNIFICANT_GROWTH"
                # Aggressive increase
                threads=$(awk "BEGIN {printf \"%.0f\", $1*1.5}" <<< "$threads")
                concurrency=$(awk "BEGIN {printf \"%.0f\", $1*2.0}" <<< "$concurrency")
            elif (( $(echo "$increase_bc >= 2.00" | bc -l) )); then
                echo -e "${YELLOW}Moderate growth: ${throughput_increase_pct}%${NC}"
                decision="MODERATE_GROWTH"
                # Moderate increase
                threads=$(awk "BEGIN {printf \"%.0f\", $1*1.2}" <<< "$threads")
                concurrency=$(awk "BEGIN {printf \"%.0f\", $1*1.5}" <<< "$concurrency")
            else
                echo -e "${YELLOW}Marginal growth: ${throughput_increase_pct}%${NC}"
                decision="MARGINAL_GROWTH"
                # Small increase
                threads=$(awk "BEGIN {printf \"%.0f\", $1*1.1}" <<< "$threads")
                concurrency=$(awk "BEGIN {printf \"%.0f\", $1*1.2}" <<< "$concurrency")
            fi
        fi
        
        # Check max caps
        if [ $threads -ge $MAX_THREADS ] && [ $concurrency -ge $MAX_CONCURRENCY ]; then
            echo -e "${YELLOW}Max caps reached: t=$MAX_THREADS, c=$MAX_CONCURRENCY${NC}"
            decision="MAX_CAPS_REACHED"
            final_decision="MAX_CAPS_REACHED"
            break
        fi
        
        # Ensure integer values
        threads=${threads%.*}
        concurrency=${concurrency%.*}
        
        # Cap at maximum
        if [ $threads -gt $MAX_THREADS ]; then
            threads=$MAX_THREADS
        fi
        if [ $concurrency -gt $MAX_CONCURRENCY ]; then
            concurrency=$MAX_CONCURRENCY
        fi
        
        # Update for next iteration
        previous_throughput=$req_per_sec
        test_sequence=$((test_sequence + 1))
        
        echo ""
    done
    
    # Summary
    echo ""
    echo "=========================================="
    echo "Benchmark Complete"
    echo "=========================================="
    echo "Final Decision: $final_decision"
    echo "Tests Run: $((test_sequence - 1))"
    echo "CSV Output: $CSV_FILE"
    echo ""
    echo -e "${GREEN}View results:${NC}"
    echo "  cat $CSV_FILE | column -t -s,"
}

# Check if wrk is installed
check_dependencies() {
    if ! command -v wrk &> /dev/null; then
        echo -e "${RED}Error: wrk is not installed${NC}"
        echo "Install wrk: https://github.com/wg/wrk"
        exit 1
    fi
    
    if ! command -v bc &> /dev/null; then
        echo -e "${RED}Error: bc is not installed${NC}"
        echo "Install bc: sudo apt-get install bc"
        exit 1
    fi
}

# Main execution
main() {
    check_dependencies
    
    # Check if service is ready
    echo "Checking service health..."
    local health_check=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL$HEALTH_ENDPOINT")
    if [ "$health_check" != "200" ]; then
        echo -e "${RED}Service health check failed: HTTP $health_check${NC}"
        echo "Ensure service is running at: $SERVICE_URL"
        exit 1
    fi
    echo -e "${GREEN}Service is healthy (HTTP 200)${NC}"
    echo ""
    
    # Warmup
    echo "Warming up service (5s)..."
    wrk -t4 -c10 -d5s "$SERVICE_URL$HEALTH_ENDPOINT" > /dev/null 2>&1
    echo ""
    
    # Run adaptive benchmark
    adaptive_benchmark
}

main "$@"