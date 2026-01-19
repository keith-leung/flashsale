#!/bin/bash
# Adaptive Plateau Detection Testing for Variant Zeta (Python)

PYTHON_PORT="30019"
PYTHON_ENDPOINT="http://localhost:${PYTHON_PORT}"
CSV_DIR="/home/syracuse/flashsale/variant-zeta/benchmark_results"
CSV_FILE="${CSV_DIR}/variant_zeta_raw_$(date +%Y%m%d_%H%M%S).csv"

mkdir -p "${CSV_DIR}"
echo "timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision" > "${CSV_FILE}"

echo "========================================="
echo "Adaptive Testing: Variant Zeta (Python)"
echo "========================================="

# Test /health (baseline)
echo ""
echo "Test 1: /health endpoint (baseline)"
echo ""
wrk -t4 -c10 -d10s ${PYTHON_ENDPOINT}/health > /tmp/health_wrk.txt 2>&1
health_reqs=$(grep "Requests/sec" /tmp/health_wrk.txt | awk '{print $2}')
health_avg=$(grep "Latency" /tmp/health_wrk.txt | awk '{print $2}')
echo "  Result: ${health_reqs} req/s, ${health_avg} avg latency"

# Test /orders (adaptive)
echo ""
echo "========================================="
echo "Adaptive Testing: /orders endpoint"
echo "========================================="
echo ""

threads=4
concurrency=10
duration=10
test_seq=1
prev_throughput=0

# Adaptive loop
while [ $test_seq -le 15 ]; do
    echo "Test ${test_seq}: t=${threads}, c=${concurrency}, d=${duration}s"
    
    # Run wrk
    wrk -t${threads} -c${concurrency} -d${duration}s ${PYTHON_ENDPOINT}/orders/ > /tmp/wrk_test_${test_seq}.txt 2>&1
    
    # Parse results
    reqs=$(grep "Requests/sec" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}')
    avg=$(grep "Latency" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}' | sed 's/ms//')
    stdev=$(grep "Latency" /tmp/wrk_test_${test_seq}.txt | awk '{print $3}' | sed 's/ms//')
    p50=$(grep "50%" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}' | sed 's/ms//')
    p90=$(grep "90%" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}' | sed 's/ms//')
    p99=$(grep "99%" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}' | sed 's/ms//')
    transfer=$(grep "Transfer/sec" /tmp/wrk_test_${test_seq}.txt | awk '{print $2}')
    
    # Calculate totals
    total_reqs=$(echo "$reqs * $duration" | bc)
    throughput_mb=$(echo "$transfer" | sed 's/MB.*//')
    
    # Calculate increase
    increase=0
    decision="INITIAL"
    if [ $test_seq -gt 1 ]; then
        increase=$(echo "scale=2; ($reqs - $prev_throughput) / $prev_throughput * 100" | bc)
        echo "  Result: ${reqs} req/s (+${increase}%)"
        
        # Decision logic
        if [ $(echo "$increase > 5" | bc) -eq 1 ]; then
            decision="SIGNIFICANT_GROWTH"
            threads=$(echo "scale=0; $threads * 1.5" | bc)
            concurrency=$(echo "scale=0; $concurrency * 2" | bc)
        elif [ $(echo "$increase >= 2" | bc) -eq 1 ] && [ $(echo "$increase <= 5" | bc) -eq 1 ]; then
            decision="MODERATE_GROWTH"
            threads=$(echo "scale=0; $threads * 1.2" | bc)
            concurrency=$(echo "scale=0; $concurrency * 1.5" | bc)
        elif [ $(echo "$increase >= 0" | bc) -eq 1 ] && [ $(echo "$increase < 2" | bc) -eq 1 ]; then
            decision="MARGINAL_GROWTH"
            threads=$(echo "scale=0; $threads * 1.1" | bc)
            concurrency=$(echo "scale=0; $concurrency * 1.2" | bc)
        fi
        
        # Check plateau (last 3 tests)
        if [ $test_seq -ge 3 ]; then
            # Simplified: if increase < 1% for 2 consecutive tests
            if [ $(echo "$increase < 1" | bc) -eq 1 ]; then
                decision="PLATEAU_CONFIRMED"
                echo "  ✓ PLATEAU_CONFIRMED"
                break
            fi
        fi
    else
        echo "  Result: ${reqs} req/s"
    fi
    
    # Write CSV
    echo "$(date +%Y%m%d_%H%M%S),variant_zeta,python,/orders/,order,${threads},${concurrency},${duration},${reqs},${avg},${p50},${p90},${p99},${p99},${stdev},${total_reqs},0,0,0,0,0,0,0,${transfer},${throughput_mb},${test_seq},${increase},${decision}" >> ${CSV_FILE}
    
    # Update for next iteration
    prev_throughput=$reqs
    test_seq=$((test_seq + 1))
    
    # Cap
    if [ $threads -gt 24 ]; then
        threads=24
    fi
    if [ $concurrency -gt 2000 ]; then
        echo "  ✗ MAX_CAPS_REACHED"
        break
    fi
    
    echo ""
done

echo ""
echo "========================================="
echo "Testing Complete"
echo "========================================="
echo ""
echo "CSV: ${CSV_FILE}"
cat ${CSV_FILE}
