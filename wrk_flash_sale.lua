-- Flash sale order stress test script
-- Generates random orders from 100K flash sale SKUs

-- Load SKU IDs from file
local sku_ids = {}
local file = io.open("/tmp/flash_sale_skus.txt", "r")
if file then
    for line in file:lines() do
        table.insert(sku_ids, line)
    end
    file:close()
else
    print("Error: SKU file not found. Creating sample SKUs...")
    -- Fallback: use first 1000 SKUs as samples
    for i = 0, 999 do
        table.insert(sku_ids, string.format("FS-%08d", i))
    end
end

print(string.format("Loaded %d SKU IDs for testing", #sku_ids))

-- Request template
request = function()
    -- Pick random SKU
    local sku_id = sku_ids[math.random(#sku_ids)]

    -- Generate order JSON
    local body = string.format([[{
        "customer_email": "stress-test-%d@flash.com",
        "line_items": [{"sku_id": "%s", "quantity": %d}]
    }]], math.random(1000000), sku_id, math.random(1, 3))

    return wrk.format("POST", "/api/v1/orders",
        {["Content-Type"] = "application/json"},
        body)
end

-- Summary
done = function(summary, latency, requests)
    io.write("------------------------------\n")
    io.write(string.format("Flash Sale Stress Test Results\n"))
    io.write("------------------------------\n")
    io.write(string.format("Requests:      %d\n", summary.requests))
    io.write(string.format("Duration:      %.2fs\n", summary.duration / 1000000))
    io.write(string.format("Req/sec:       %.2f\n", summary.requests / (summary.duration / 1000000)))
    io.write(string.format("Avg Latency:   %.2fms\n", latency.mean / 1000))
    io.write(string.format("P50 Latency:   %.2fms\n", latency:percentile(50) / 1000))
    io.write(string.format("P99 Latency:   %.2fms\n", latency:percentile(99) / 1000))
    io.write(string.format("Max Latency:   %.2fms\n", latency.max / 1000))
    io.write(string.format("Success Rate:  %.2f%%\n", (summary.requests - summary.errors.status - summary.errors.connect - summary.errors.read - summary.errors.write - summary.errors.timeout) / summary.requests * 100))
    io.write("------------------------------\n")
end
