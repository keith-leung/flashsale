#!/bin/bash
# =============================================================================
# Adaptive Plateau Detection for Variant Zeta
# =============================================================================

set -e

# Configuration
PYTHON_API="http://localhost:30019"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CSV_FILE="./benchmark_results/variant_z_adaptive_${TIMESTAMP}.csv"
BASE_DURATION=10

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Create CSV directory
mkdir -p ./benchmark_results

# Initialize CSV
echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "$CSV_FILE"

echo "✓ CSV initialized: $CSV_FILE"

# Parse wrk output and extract metrics
parse_wrk() {
    local wrk_output="$1"
    
    req_per_sec=$(echo "$wrk_output" | grep "Requests/sec:" | awk '{print $2}')
    avg_latency=$(echo "$wrk_output" | grep "Latency" | awk '{print $2}' | sed 's/ms//')
    stdev_latency=$(echo "$wrk_output" | awk '/^    Latency/ {print $4}' | sed 's/us//')
    stdev_latency=$(echo "scale=4; $stdev_latency / 1000" | bc)
    
    p50_latency=$(echo "$wrk_output" | grep "50%" | awk '{print $2}' | sed 's/ms//')
    p90_latency=$(echo "$wrk_output" | grep "90%" | awk '{print $2}' | sed 's/ms//')
    p99_latency=$(echo "$wrk_output" | grep "99%" | awk '{print $2}' | sed 's/ms//')
    
    transfer_mb=$(echo "$wrk_output" | grep "Transfer/sec:" | awk '{print $2}' | sed 's/MB.*//')
    
    echo "$req_per_sec $avg_latency $stdev_latency $p50_latency $p90_latency $p99_latency $transfer_mb"
}

# Write CSV row
write_csv() {
    local test_seq="$1"
    local t="$2"
    local c="$3"
    local d="$4"
    local req="$5"
    local avg="$6"
    local stdev="$7"
    local p50="$8"
    local p90="$9"
    local p99="$10"
    local transfer="$11"
    local increase="$12"
    local decision="$13"
    
    total_req=$(echo "$req * $d" | bc)
    total_errors=0
    error_pct=0
    non_2xx_3xx=0
    socket_connect=0
    socket_read=0
    socket_write=0
    socket_timeout=0
    throughput_mb=$transfer
    
    csv_row="$TIMESTAMP,variant_z,python,/orders/,order,$t,$c,$d,$req,$avg,$stdev,$p50,$p90,$p99,$p99,$stdev,$total_req,$total_errors,$error_pct,$non_2xx_3xx,$socket_connect,$socket_read,$socket_write,$socket_timeout,$transfer,$throughput_mb,$test_seq,$increase,$decision"
    echo "$csv_row" >> "$CSV_FILE"
}

# Main adaptive loop
echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${BLUE}║  Adaptive Plateau Detection: /orders/ endpoint           ${BOLD}${BLUE}║${NC}"
echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════╝${NC}"

threads=4
concurrency=10
duration=$BASE_DURATION

prev_throughput=0
test_seq=1
decision="INITIAL"
throughputs=()

while [ $test_seq -le 20 ]; do
    echo -e "\n${YELLOW}Test $test_seq: t=$threads, c=$concurrency, d=${duration}s${NC}"
    echo "─────────────────────────────────────────────────────────"
    
    # Run wrk
    wrk_output=$(wrk -t$threads -c$concurrency -d${duration}s --latency -s /tmp/wrk_final_test.lua "$PYTHON_API/orders/" 2>&1)
    
    # Parse output
    parsed=$(parse_wrk "$wrk_output")
    read req avg stdev p50 p90 p99 transfer <<< "$parsed"
    
    echo -e "${GREEN}Result: $req req/s, ${avg}ms avg${NC}"
    
    # Store throughput
    throughputs+=("$req")
    
    # Calculate increase
    increase=0
    increase_pct=0
    if [ $test_seq -gt 1 ]; then
        increase=$(echo "$req - $prev_throughput" | bc -l)
        increase_pct=$(echo "scale=2; ($req - $prev_throughput) / $prev_throughput * 100" | bc -l)
        echo -e "${BLUE}Increase: ${increase_pct}%${NC}"
    fi
    
    # Check caps
    if [ $threads -eq 24 ] && [ $concurrency -ge 2000 ]; then
        echo -e "${YELLOW}✗ MAX_CAPS_REACHED${NC}"
        decision="MAX_CAPS_REACHED"
        write_csv "$test_seq" "$threads" "$concurrency" "$duration" "$req" "$avg" "$stdev" "$p50" "$p90" "$p99" "$transfer" "$increase_pct" "$decision"
        break
    fi
    
    # Decision logic
    if [ $test_seq -eq 1 ]; then
        decision="INITIAL"
    elif [ $(echo "$increase_pct > 5" | bc -l) -eq 1 ]; then
        decision="SIGNIFICANT_GROWTH"
        threads=$(echo "scale=0; $threads * 1.5" | bc -l)
        concurrency=$(echo "scale=0; $concurrency * 2" | bc -l)
        echo -e "${GREEN}Decision: SIGNIFICANT_GROWTH${NC}"
    elif [ $(echo "$increase_pct >= 2" | bc -l) -eq 1 ] && [ $(echo "$increase_pct <= 5" | bc -l) -eq 1 ]; then
        decision="MODERATE_GROWTH"
        threads=$(echo "scale=0; $threads * 1.2" | bc -l)
        concurrency=$(echo "scale=0; $concurrency * 1.5" | bc -l)
        echo -e "${YELLOW}Decision: MODERATE_GROWTH${NC}"
    elif [ $(echo "$increase_pct >= 0" | bc -l) -eq 1 ] && [ $(echo "$increase_pct < 2" | bc -l) -eq 1 ]; then
        decision="MARGINAL_GROWTH"
        threads=$(echo "scale=0; $threads * 1.1" | bc -l)
        concurrency=$(echo "scale=0; $concurrency * 1.2" | bc -l)
        echo -e "${YELLOW}Decision: MARGINAL_GROWTH${NC}"
    fi
    
    # Plateau detection
    if [ $test_seq -ge 3 ]; then
        last3=("${throughputs[@]: -3}")
        mean=$(echo "scale=2; (${last3[0]} + ${last3[1]} + ${last3[2]}) / 3" | bc -l)
        variance=$(echo "scale=4; ((${last3[0]} - $mean)^2 + (${last3[1]} - $mean)^2 + (${last3[2]} - $mean)^2) / 3" | bc -l)
        stdev=$(echo "scale=4; sqrt($variance)" | bc -l)
        cv=$(echo "scale=2; ($stdev / $mean) * 100" | bc -l)
        
        echo -e "${BLUE}CV: ${cv}%${NC}"
        
        if [ $(echo "$cv < 2" | bc -l) -eq 1 ]; then
            echo -e "${GREEN}✓ PLATEAU_CONFIRMED${NC}"
            decision="PLATEAU_CONFIRMED"
            write_csv "$test_seq" "$threads" "$concurrency" "$duration" "$req" "$avg" "$stdev" "$p50" "$p90" "$p99" "$transfer" "$increase_pct" "$decision"
            break
        fi
    fi
    
    # Adjust duration
    if [ $concurrency -gt 500 ]; then
        duration=$((BASE_DURATION + 5))
    fi
    if [ $concurrency -gt 1000 ]; then
        duration=$((BASE_DURATION + 10))
    fi
    
    # Cap threads
    if [ $threads -gt 24 ]; then
        threads=24
    fi
    
    # Write CSV
    write_csv "$test_seq" "$threads" "$concurrency" "$duration" "$req" "$avg" "$stdev" "$p50" "$p90" "$p99" "$transfer" "$increase_pct" "$decision"
    
    # Update for next
    prev_throughput=$req
    test_seq=$((test_seq + 1))
    
    if [ $test_seq -gt 20 ]; then
        echo -e "${YELLOW}✗ MAX_TESTS_REACHED${NC}"
        decision="MAX_TESTS_REACHED"
        break
    fi
done

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Adaptive Testing Complete                         ${BOLD}${GREEN}║${NC}"
echo -e "${BOLD}${GREEN}║  Final Decision: $decision                              ${BOLD}${GREEN}║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}CSV: $CSV_FILE${NC}"

exit 0
