-- wrk order script for Java Variant V (flat structure)
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- Flat structure for Java service (camelCase)
wrk.body = [[{"customerEmail": "test@example.com", "skuId": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab", "quantity": 1, "unitPrice": 49.99, "flashSaleCampaignId": "test-flash-campaign-001"}]]

-- Request counter
local counter = 0
local status_201 = 0
local status_409 = 0
local others = 0

-- Process response
response = function(status, headers, body)
    counter = counter + 1
    if status == 201 then
        status_201 = status_201 + 1
    elseif status == 409 then
        status_409 = status_409 + 1
    else
        others = others + 1
    end
end

-- Summary output
done = function(summary, latency, requests)
    io.write(string.format("\n=== Java Order Endpoint Results ===\n"))
    io.write(string.format("Total Requests: %d\n", counter))
    io.write(string.format("HTTP 201 (Created): %d\n", status_201))
    io.write(string.format("HTTP 409 (Conflict): %d\n", status_409))
    io.write(string.format("Other Status: %d\n", others))
    io.write(string.format("Throughput: %.2f req/s\n", summary.requests/(summary.duration/1000000)))
    io.write(string.format("Avg Latency: %.2fms\n", latency.mean/1000))
    io.write(string.format("P99 Latency: %.2fms\n", latency:percentile(0.99)/1000))
end
