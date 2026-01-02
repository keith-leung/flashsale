#!/bin/bash
#############################################################################
# Complete Benchmark Suite - Variant Y (Pure Database)
#############################################################################
#
# This script runs plateau detection tests on all service/endpoint
# combinations to generate a complete performance profile.
#
# USAGE:
#   ./run_complete_benchmark.sh
#
# OUTPUTS:
#   - Individual CSV files for each test in ./benchmark_results/
#   - Summary report in ./benchmark_results/summary_TIMESTAMP.txt
#
#############################################################################

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./benchmark_results"
SUMMARY_FILE="${RESULTS_DIR}/summary_${TIMESTAMP}.txt"

# Create results directory
mkdir -p "$RESULTS_DIR"

echo "=============================================================================" | tee "$SUMMARY_FILE"
echo "Complete Benchmark Suite - Variant Y (Pure Database)" | tee -a "$SUMMARY_FILE"
echo "Started: $(date)" | tee -a "$SUMMARY_FILE"
echo "=============================================================================" | tee -a "$SUMMARY_FILE"
echo "" | tee -a "$SUMMARY_FILE"

# Test configurations: SERVICE ENDPOINT DESCRIPTION
tests=(
    "python /health 'Python Health Check'"
    "java /actuator/health 'Java Health Check'"
    "csharp /health 'C# Health Check'"
    "nginx /health 'Nginx Health Check (Round-Robin)'"
    "python /api/v1/orders 'Python Order Creation'"
    "java /api/v1/orders 'Java Order Creation'"
    "csharp /api/v1/orders 'C# Order Creation'"
    "nginx /api/v1/orders 'Nginx Order Creation (Round-Robin)'"
)

total_tests=${#tests[@]}
completed=0

for test in "${tests[@]}"; do
    # Parse test configuration
    read -r service endpoint description <<< "$test"
    description=$(echo "$description" | tr -d "'")

    ((completed++))

    echo "-------------------------------------------------------------------" | tee -a "$SUMMARY_FILE"
    echo "[${completed}/${total_tests}] Testing: $description" | tee -a "$SUMMARY_FILE"
    echo "Service: $service | Endpoint: $endpoint" | tee -a "$SUMMARY_FILE"
    echo "-------------------------------------------------------------------" | tee -a "$SUMMARY_FILE"
    echo "" | tee -a "$SUMMARY_FILE"

    # Run plateau detection benchmark
    ./benchmark_plateau.sh "$service" "$endpoint" | tee -a "${RESULTS_DIR}/log_${service}_${endpoint//\//_}_${TIMESTAMP}.txt"

    # Extract plateau result from CSV
    csv_pattern="${RESULTS_DIR}/plateau_${service}_*.csv"
    latest_csv=$(ls -t $csv_pattern 2>/dev/null | head -1)

    if [ -f "$latest_csv" ]; then
        # Get the last row before plateau or the highest concurrency tested
        plateau_row=$(grep ",yes$" "$latest_csv" | head -1)
        if [ -z "$plateau_row" ]; then
            # No plateau detected, get last row
            plateau_row=$(tail -1 "$latest_csv")
        fi

        # Parse results
        IFS=',' read -r concurrency throughput avg_lat p50 p90 p99 increase plateau_flag <<< "$plateau_row"

        echo "RESULTS:" | tee -a "$SUMMARY_FILE"
        echo "  Max Throughput:  $throughput req/s @ $concurrency connections" | tee -a "$SUMMARY_FILE"
        echo "  Avg Latency:     $avg_lat ms" | tee -a "$SUMMARY_FILE"
        echo "  P90 Latency:     $p90 ms" | tee -a "$SUMMARY_FILE"
        echo "  P99 Latency:     $p99 ms" | tee -a "$SUMMARY_FILE"
        if [ "$plateau_flag" = "yes" ]; then
            echo "  Status:          PLATEAU DETECTED ✓" | tee -a "$SUMMARY_FILE"
        else
            echo "  Status:          No plateau (tested up to $concurrency connections)" | tee -a "$SUMMARY_FILE"
        fi
        echo "" | tee -a "$SUMMARY_FILE"
    else
        echo "  ERROR: Could not find results file" | tee -a "$SUMMARY_FILE"
        echo "" | tee -a "$SUMMARY_FILE"
    fi

    # Brief pause between tests
    sleep 5
done

echo "=============================================================================" | tee -a "$SUMMARY_FILE"
echo "Benchmark Suite Complete!" | tee -a "$SUMMARY_FILE"
echo "Completed: $(date)" | tee -a "$SUMMARY_FILE"
echo "=============================================================================" | tee -a "$SUMMARY_FILE"
echo "" | tee -a "$SUMMARY_FILE"
echo "Results saved to: $RESULTS_DIR" | tee -a "$SUMMARY_FILE"
echo "Summary report: $SUMMARY_FILE" | tee -a "$SUMMARY_FILE"
echo "" | tee -a "$SUMMARY_FILE"
echo "To view all CSV results:" | tee -a "$SUMMARY_FILE"
echo "  ls -lh ${RESULTS_DIR}/plateau_*.csv" | tee -a "$SUMMARY_FILE"
echo "" | tee -a "$SUMMARY_FILE"
