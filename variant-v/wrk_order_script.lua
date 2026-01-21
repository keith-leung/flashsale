-- wrk order script for Variant V
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- Payload for single-SKU order
wrk.body = [[{"customer_email": "test@example.com", "items": [{"sku_id": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab", "quantity": 1, "unit_price": 49.99}], "flash_sale_campaign_id": "test-flash-campaign-001"}]]

-- Request counter
local counter = 0
local errors = 0
local created = 0
local conflicts = 0

-- Process response
response = function(status, headers, body)
    counter = counter + 1
    if status == 201 then
        created = created + 1
    elseif status == 409 then
        conflicts = conflicts + 1
    else
        errors = errors + 1
    end
end

-- Summary output
done = function(summary, latency, requests)
    io.write(string.format("\n=== Order Endpoint Results ===\n"))
    io.write(string.format("Total Requests: %d\n", counter))
    io.write(string.format("HTTP 201 (Created): %d\n", created))
    io.write(string.format("HTTP 409 (Conflict): %d\n", conflicts))
    io.write(string.format("Errors: %d\n", errors))
    io.write(string.format("Throughput: %.2f req/s\n", summary.requests/(summary.duration/1000000)))
    io.write(string.format("Avg Latency: %.2fms\n", latency.mean/1000))
    io.write(string.format("P99 Latency: %.2fms\n", latency:percentile(0.99)/1000))
end
