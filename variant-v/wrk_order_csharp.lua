-- wrk order script for C# Variant V (items array structure)
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- Array structure for C# service (similar to Python)
wrk.body = [[{"customer_email": "test@example.com", "items": [{"sku_id": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab", "quantity": 1, "unit_price": 49.99}], "flash_sale_campaign_id": "test-flash-campaign-001"}]]

-- Request counter
local counter = 0

-- Summary output
done = function(summary, latency, requests)
    io.write(string.format("\n=== C# Order Endpoint Results ===\n"))
    io.write(string.format("Total Requests: %d\n", summary.requests))
    io.write(string.format("Throughput: %.2f req/s\n", summary.requests/(summary.duration/1000000)))
    io.write(string.format("Avg Latency: %.2fms\n", latency.mean/1000))
    io.write(string.format("P99 Latency: %.2fms\n", latency:percentile(0.99)/1000))
    io.write(string.format("Non-2xx responses: %d\n", summary.errors.status))
end
