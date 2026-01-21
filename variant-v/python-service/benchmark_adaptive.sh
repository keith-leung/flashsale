#!/bin/bash
# Adaptive Health Endpoint Benchmark for Variant V
# Inspired by variant-y approach but adapted for campaign-aware design

set -e

URL="${1:-http://localhost:8000/health}"
MIN_REQUESTS=10000  # Minimum throughput target
MIN_DURATION=30s

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}"
echo "═══════════════════════════════════════════════════════════════════"
echo "      Variant V - Adaptive Health Benchmark"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

if ! command -v wrk &> /dev/null; then
    echo "ERROR: wrk is not installed"
    exit 1
fi

function run_benchmark() {
    local threads=$1
    local connections=$2
    local duration=$3
    
    echo -e "${YELLOW}[Testing] ${threads} threads, ${connections} connections${NC}"
    
    wrk -t${threads} -c${connections} -d${duration} --latency ${URL} 2>&1 | tee /tmp/benchmark_output.txt
    
    # Extract requests/sec
    THROUGHPUT=$(grep "Requests/sec" /tmp/benchmark_output.txt | awk '{print $2}' | cut -d. -f1)
    
    echo $THROUGHPUT
}

echo "Target: >${MIN_REQUESTS} req/s"
echo ""

# Phase 1: Aggressive baseline test
echo -e "${BOLD}${GREEN}Phase 1: Aggressive Baseline${NC}"
THROUGHPUT=$(run_benchmark 12 400 30s)
echo -e "${BLUE}Baseline: ${THROUGHPUT} req/s${NC}"

if [ "$THROUGHPUT" -ge $((MIN_REQUESTS * 4)) ]; then
    echo -e "${GREEN}✓ Excellent! Exceeds target by 4x${NC}"
    
    # Stress test
    echo ""
    echo -e "${YELLOW}[Stress Test]${NC}"
    run_benchmark 24 800 30s
elif [ "$THROUGHPUT" -ge $((MIN_REQUESTS * 2)) ]; then
    echo -e "${GREEN}✓ Good! Exceeds target by 2x${NC}"
    
    # Moderate stress
    echo ""
    echo -e "${YELLOW}[Stress Test]${NC}"
    run_benchmark 16 600 30s
elif [ "$THROUGHPUT" -ge $MIN_REQUESTS ]; then
    echo -e "${YELLOW}✓ Acceptable. Meets minimum target${NC}"
    
    # Light optimization
    echo ""
    echo -e "${YELLOW}[Light Optimization Test]${NC}"
    run_benchmark 12 300 30s
else
    echo -e "${RED}✗ Below target. Analyzing...${NC}"
    
    # Debug mode
    echo ""
    echo -e "${YELLOW}[Debug Mode] Running multiple configurations${NC}"
    
    echo "Low concurrency:"
    run_benchmark 4 100 30s
    
    echo ""
    echo "Medium concurrency:"
    run_benchmark 8 200 30s
    
    echo ""
    echo "High concurrency:"
    run_benchmark 16 400 30s
fi

echo ""
echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
