#!/bin/bash
# Peak Performance Finder for Python Flash Sale Service
# Adaptively finds the optimal concurrency for maximum RPS

CAMPAIGN_ID="99999999-8888-7777-6666-555544443333"
SKU_ID="11111111-2222-3333-4444-555555555555"
BASE_URL="http://localhost:30013/api/v1/orders"
RESULT_DIR="/home/syracuse/flashsale/benchmark_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_CSV="${RESULT_DIR}/python_peak_${TIMESTAMP}.csv"

mkdir -p "$RESULT_DIR"

# Create Lua script for wrk
cat > /tmp/order_benchmark.lua << LUAEOF
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

local counter = 0
local campaign_id = "${CAMPAIGN_ID}"
local sku_id = "${SKU_ID}"

request = function()
    counter = counter + 1
    local body = string.format([[{
        "customer_email": "bench%d@test.com",
        "flash_sale_campaign_id": "%s",
        "line_items": [{"sku_id": "%s", "quantity": 1}]
    }]], counter, campaign_id, sku_id)
    return wrk.format(nil, nil, nil, body)
end
LUAEOF

# CSV Header
echo "concurrency,threads,duration,total_requests,rps,avg_latency_ms,p99_latency,errors,pool_consumed" > "$RESULT_CSV"

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║        PYTHON FLASH SALE - PEAK PERFORMANCE FINDER                    ║"
echo "╠═══════════════════════════════════════════════════════════════════════╣"
echo "║  Campaign: BENCHMARK-HIGH-VOLUME (100,000 items)                      ║"
echo "║  Redis Pool: 40,000 items                                             ║"
echo "║  Finding optimal concurrency for maximum RPS...                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

get_pool() {
    podman exec flash-redis-a redis-cli GET "fs:${CAMPAIGN_ID}:redis_pool:spu_counter" 2>/dev/null || echo "0"
}

best_rps=0
best_concurrency=0
best_latency=""

# Test configurations - focus on finding peak
# Format: threads connections duration
configs=(
    "2 20 5s"
    "2 40 5s"
    "4 60 5s"
    "4 80 5s"
    "4 100 5s"
    "4 120 5s"
    "4 140 5s"
    "4 160 5s"
    "8 180 5s"
    "8 200 5s"
    "8 250 5s"
    "8 300 5s"
)

for config in "${configs[@]}"; do
    read -r threads connections duration <<< "$config"

    pool_before=$(get_pool)

    # Run benchmark
    result=$(wrk -t${threads} -c${connections} -d${duration} --latency -s /tmp/order_benchmark.lua "$BASE_URL" 2>&1)

    # Parse results
    rps=$(echo "$result" | grep "Requests/sec:" | awk '{print $2}')
    avg_lat=$(echo "$result" | grep "Latency" | head -1 | awk '{print $2}')
    p99=$(echo "$result" | grep "99%" | awk '{print $2}')
    total=$(echo "$result" | grep "requests in" | awk '{print $1}')
    errors=$(echo "$result" | grep -E "Socket errors|Non-2xx" | head -1)

    pool_after=$(get_pool)
    consumed=$((pool_before - pool_after))

    # Convert RPS to number for comparison
    rps_num=$(echo "$rps" | sed 's/[^0-9.]//g')

    # Check if this is the best
    is_best=""
    if (( $(echo "$rps_num > $best_rps" | bc -l 2>/dev/null || echo 0) )); then
        best_rps=$rps_num
        best_concurrency=$connections
        best_latency=$avg_lat
        is_best=" ★ NEW BEST"
    fi

    # Display
    printf "c=%-3d t=%-1d │ RPS: %8s │ Latency: %8s │ P99: %8s │ Pool: %5d→%5d%s\n" \
        "$connections" "$threads" "$rps" "$avg_lat" "$p99" "$pool_before" "$pool_after" "$is_best"

    # Write to CSV
    echo "${connections},${threads},${duration},${total},${rps},${avg_lat},${p99},${errors:-none},${consumed}" >> "$RESULT_CSV"

    sleep 1
done

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                         PEAK PERFORMANCE RESULT                        ║"
echo "╠═══════════════════════════════════════════════════════════════════════╣"
printf "║  Best RPS:         %-50s  ║\n" "${best_rps}"
printf "║  At Concurrency:   %-50s  ║\n" "${best_concurrency}"
printf "║  Avg Latency:      %-50s  ║\n" "${best_latency}"
echo "╠═══════════════════════════════════════════════════════════════════════╣"
echo "║  Results saved to: ${RESULT_CSV}"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Show final pool status
echo "Final Redis Pool: $(get_pool)"
echo ""
echo "=== CSV Results ==="
cat "$RESULT_CSV"
