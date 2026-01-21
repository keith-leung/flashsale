#!/bin/bash
# Benchmark Nginx load balancer for Variant V

echo "=== Nginx Variant V - Load Balancer Test ==="
echo "Endpoint: POST http://localhost:8447/api/v1/orders"
echo "Concurrency: c=50, Threads: t=4, Duration: 30s"
echo ""

# Create temporary JSON payload file
JSON_PAYLOAD='{"customer_email":"test@example.com","sku_id":"6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab","quantity":1,"unit_price":49.99,"flash_sale_campaign_id":"test-flash-campaign-001"}'

# Run wrk benchmark
wrk -t4 -c50 -d30s \
  -H "Content-Type: application/json" \
  --script <(cat <<'EOF'
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = '{"customer_email":"test@example.com","sku_id":"6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab","quantity":1,"unit_price":49.99,"flash_sale_campaign_id":"test-flash-campaign-001"}'
EOF
) \
  http://localhost:8447/api/v1/orders 2>&1 | grep -E "(Requests/sec|Latency|Non-2xx)"

echo ""
echo "Test complete."