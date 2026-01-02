#!/bin/bash
#############################################################################
# Plateau Detection Benchmark - Variant Y (Pure Database)
#############################################################################
#
# This script implements automated plateau testing to find the maximum
# sustainable throughput for each service/endpoint combination.
#
# METHODOLOGY:
# 1. Start with low concurrency (10 connections)
# 2. Incrementally increase concurrency
# 3. For each level, run 30-second test and measure throughput
# 4. Calculate throughput increase % vs previous level
# 5. PLATEAU DETECTED when: throughput increase <5% with 50%+ more connections
# 6. Log all results to CSV for analysis
#
# USAGE:
#   ./benchmark_plateau.sh [SERVICE] [ENDPOINT]
#
# EXAMPLES:
#   ./benchmark_plateau.sh python /health
#   ./benchmark_plateau.sh java /api/v1/orders
#   ./benchmark_plateau.sh csharp /api/v1/orders
#   ./benchmark_plateau.sh nginx /health
#
#############################################################################

set -euo pipefail

# Configuration
TEST_DURATION="30s"
WARMUP_DURATION="5s"
CONCURRENCY_LEVELS=(10 25 50 75 100 150 200 300 400 500 750 1000)
PLATEAU_THRESHOLD=5  # % increase threshold
CONNECTION_INCREASE_MIN=50  # Minimum % increase in connections to check plateau
RESULTS_DIR="./benchmark_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Service port mapping
declare -A SERVICE_PORTS
SERVICE_PORTS[python]="8000"
SERVICE_PORTS[java]="8081"
SERVICE_PORTS[csharp]="8082"
SERVICE_PORTS[nginx]="8443"

# Parse arguments
SERVICE="${1:-python}"
ENDPOINT="${2:-/health}"
PORT="${SERVICE_PORTS[$SERVICE]:-8000}"

# Determine protocol (nginx uses HTTPS, others use HTTP)
if [ "$SERVICE" = "nginx" ]; then
    PROTOCOL="https"
    EXTRA_FLAGS="-k"  # Skip SSL verification for self-signed cert
else
    PROTOCOL="http"
    EXTRA_FLAGS=""
fi

URL="${PROTOCOL}://localhost:${PORT}${ENDPOINT}"

# Create results directory
mkdir -p "$RESULTS_DIR"
CSV_FILE="${RESULTS_DIR}/plateau_${SERVICE}_${TIMESTAMP}.csv"

# Write CSV header
echo "concurrency,requests_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,throughput_increase_pct,plateau_detected" > "$CSV_FILE"

echo "============================================================================="
echo "Plateau Detection Benchmark - Variant Y"
echo "============================================================================="
echo "Service:    $SERVICE"
echo "Endpoint:   $ENDPOINT"
echo "URL:        $URL"
echo "Duration:   $TEST_DURATION (per test)"
echo "Results:    $CSV_FILE"
echo "============================================================================="
echo ""

# Warmup
echo "[WARMUP] Running ${WARMUP_DURATION} warmup..."
wrk -t4 -c10 -d${WARMUP_DURATION} ${EXTRA_FLAGS} "${URL}" > /dev/null 2>&1 || true
echo "✓ Warmup complete"
echo ""

# Track previous throughput for plateau detection
prev_throughput=0
plateau_detected="no"

# Run concurrency sweep
for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
    if [ "$plateau_detected" = "yes" ]; then
        echo "[INFO] Plateau already detected, skipping concurrency ${concurrency}"
        continue
    fi

    echo "-------------------------------------------------------------------"
    echo "[TEST] Concurrency: ${concurrency} connections"
    echo "-------------------------------------------------------------------"

    # Calculate thread count (max 12, at least 4)
    threads=$((concurrency / 10))
    if [ $threads -lt 4 ]; then
        threads=4
    elif [ $threads -gt 12 ]; then
        threads=12
    fi

    # Run wrk benchmark
    result=$(wrk -t${threads} -c${concurrency} -d${TEST_DURATION} ${EXTRA_FLAGS} "${URL}" 2>&1)

    # Parse results using awk
    requests_per_sec=$(echo "$result" | grep "Requests/sec:" | awk '{print $2}')
    avg_latency=$(echo "$result" | grep "Latency" | awk '{print $2}')

    # Convert latency to milliseconds
    if [[ $avg_latency =~ ([0-9.]+)([a-z]+) ]]; then
        value="${BASH_REMATCH[1]}"
        unit="${BASH_REMATCH[2]}"
        case $unit in
            us) avg_latency_ms=$(echo "scale=2; $value / 1000" | bc) ;;
            ms) avg_latency_ms=$value ;;
            s) avg_latency_ms=$(echo "scale=2; $value * 1000" | bc) ;;
            *) avg_latency_ms=$value ;;
        esac
    else
        avg_latency_ms="0"
    fi

    # Parse percentile latencies
    p50_latency=$(echo "$result" | grep "50%" | awk '{print $2}')
    p90_latency=$(echo "$result" | grep "90%" | awk '{print $2}')
    p99_latency=$(echo "$result" | grep "99%" | awk '{print $2}')

    # Convert percentile latencies to ms
    for percentile in p50 p90 p99; do
        var_name="${percentile}_latency"
        val="${!var_name}"
        if [[ $val =~ ([0-9.]+)([a-z]+) ]]; then
            value="${BASH_REMATCH[1]}"
            unit="${BASH_REMATCH[2]}"
            case $unit in
                us) eval "${var_name}_ms=$(echo "scale=2; $value / 1000" | bc)" ;;
                ms) eval "${var_name}_ms=$value" ;;
                s) eval "${var_name}_ms=$(echo "scale=2; $value * 1000" | bc)" ;;
                *) eval "${var_name}_ms=$value" ;;
            esac
        else
            eval "${var_name}_ms=0"
        fi
    done

    # Calculate throughput increase
    if [ "$prev_throughput" = "0" ] || [ -z "$prev_throughput" ]; then
        throughput_increase_pct="N/A"
    else
        throughput_increase_pct=$(echo "scale=2; (($requests_per_sec - $prev_throughput) / $prev_throughput) * 100" | bc)
    fi

    # Check for plateau detection
    if [ "$throughput_increase_pct" != "N/A" ]; then
        # Calculate connection increase percentage
        prev_concurrency=${CONCURRENCY_LEVELS[$((${#CONCURRENCY_LEVELS[@]} - 1))]}
        for i in "${!CONCURRENCY_LEVELS[@]}"; do
            if [ "${CONCURRENCY_LEVELS[$i]}" = "$concurrency" ] && [ $i -gt 0 ]; then
                prev_concurrency="${CONCURRENCY_LEVELS[$((i-1))]}"
                break
            fi
        done

        conn_increase_pct=$(echo "scale=2; (($concurrency - $prev_concurrency) / $prev_concurrency) * 100" | bc)

        # Check plateau condition: throughput increase <5% AND connection increase >=50%
        is_below_threshold=$(echo "$throughput_increase_pct < $PLATEAU_THRESHOLD" | bc -l)
        is_above_min_increase=$(echo "$conn_increase_pct >= $CONNECTION_INCREASE_MIN" | bc -l)

        if [ "$is_below_threshold" = "1" ] && [ "$is_above_min_increase" = "1" ]; then
            plateau_detected="yes"
            echo ""
            echo "🎯 PLATEAU DETECTED!"
            echo "   Throughput increased only ${throughput_increase_pct}% with ${conn_increase_pct}% more connections"
            echo "   Maximum sustainable throughput: ${prev_throughput} req/s at ${prev_concurrency} connections"
            echo ""
        fi
    fi

    # Write to CSV
    echo "${concurrency},${requests_per_sec},${avg_latency_ms},${p50_latency_ms},${p90_latency_ms},${p99_latency_ms},${throughput_increase_pct},${plateau_detected}" >> "$CSV_FILE"

    # Display results
    echo "Results:"
    echo "  Throughput:      ${requests_per_sec} req/s"
    echo "  Avg Latency:     ${avg_latency_ms} ms"
    echo "  P50 Latency:     ${p50_latency_ms} ms"
    echo "  P90 Latency:     ${p90_latency_ms} ms"
    echo "  P99 Latency:     ${p99_latency_ms} ms"
    if [ "$throughput_increase_pct" != "N/A" ]; then
        echo "  Increase:        ${throughput_increase_pct}% vs previous level"
    fi
    echo ""

    # Update previous throughput
    prev_throughput=$requests_per_sec

    # Brief pause between tests
    sleep 2
done

echo "============================================================================="
echo "Benchmark Complete!"
echo "============================================================================="
echo "Results saved to: $CSV_FILE"
echo ""
echo "To view results:"
echo "  cat $CSV_FILE | column -t -s,"
echo ""
echo "To analyze plateau:"
echo "  grep 'yes' $CSV_FILE"
echo "============================================================================="
