#!/bin/bash
# Simple performance benchmark for orders endpoint using wrk

set -e

API_URL="http://localhost:30017/api/v1/orders"

# Prepare JSON payload
JSON_PAYLOAD='{"customer_email":"test@example.com","items":[{"sku_id":"6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab","quantity":1,"unit_price":49.99}],"flash_sale_campaign_id":"test-flash-campaign-001"}'

# Base64 encode the payload for wrk
ENCODED_PAYLOAD=$(echo -n "$JSON_PAYLOAD" | base64 -w 0)

echo "Variant V Order Endpoint - Simple Performance Test"
echo "==================================================="
echo "Endpoint: POST $API_URL"
echo "Payload:  $JSON_PAYLOAD"
echo ""

# Run progressive load test
echo "Phase 1: Low concurrency (10 connections, 30s)"
wrk -t4 -c10 -d30s --timeout 5s \
    -H "Content-Type: application/json" \
    --script <(cat <<EOF
wrk.method = "POST"
wrk.body   = "$JSON_PAYLOAD"
wrk:done(function(summary, latency, requests)
    io.write("\nResults:\\n")
    io.write(string.format("  Requests/sec: %.2f\\n", summary.requests/(summary.duration/1000000)))
    io.write(string.format("  Avg Latency:  %.2fms\\n", latency.mean/1000))
    io.write(string.format("  Max Latency:  %.2fms\\n", latency.max/1000))
end
EOF
) \
    "$API_URL" || echo "Phase 1 failed"

echo ""
echo "Phase 2: Medium concurrency (50 connections, 30s)"
wrk -t8 -c50 -d30s --timeout 5s \
    -H "Content-Type: application/json" \
    --script <(cat <<EOF  
wrk.method = "POST"
wrk.body   = "$JSON_PAYLOAD"
wrk:done(function(summary, latency, requests)
    io.write("\nResults:\\n")
    io.write(string.format("  Requests/sec: %.2f\\n", summary.requests/(summary.duration/1000000)))
    io.write(string.format("  Avg Latency:  %.2fms\\n", latency.mean/1000))
    io.write(string.format("  Max Latency:  %.2fms\\n", latency.max/1000))
end
EOF
) \
    "$API_URL" || echo "Phase 2 failed"
