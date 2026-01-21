#!/bin/bash
# Variant U Verification Script
# Aligned with SACRED VERIFICATION methodology

set -e

DURATION="${1:-10}"  # Default 10s per test
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="./benchmark_results"
VARIANT_NAME="variant_u"

# Color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Variant U Service Configuration
PYTHON_SERVICE="flash-python-u"
JAVA_SERVICE="flash-java-u"
CSHARP_SERVICE="flash-csharp-u"
NGINX_SERVICE="flash-nginx-u"
MARIADB_SERVICE="flash-mariadb-u"
REDIS_SERVICE="flash-redis-u"

PYTHON_PORT="30015"
JAVA_PORT="8018"
CSHARP_PORT="30016"
NGINX_PORT="8447"

CSV_FILE="${RESULTS_DIR}/${VARIANT_NAME}_raw_${TIMESTAMP}.csv"

# Initialize CSV with SACRED schema
echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "$CSV_FILE"

# Run adaptive tests for Python /health
bash ./lib/plateau_detector.sh "10.91.0.5:8000" "/health" "health" "$PYTHON_SERVICE" "$CSV_FILE" "$DURATION"

echo -e "${GREEN}✓ Variant U verification script created${NC}"
echo -e "${GREEN}Next: Run adaptive benchmark on Python /health endpoint"}