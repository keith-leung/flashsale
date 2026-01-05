-- wrk Lua script for testing flash sale orders
-- Usage: wrk -t12 -c50 -d10s -s wrk_order_test.lua http://localhost:8017/api/v1/orders

-- Test campaign and SKU IDs
local campaign_id = "650e8400-e29b-41d4-a716-446655440000"
local sku_id = "650e8400-e29b-41d4-a716-446655440001"

-- Generate unique order IDs
local counter = 0

request = function()
    counter = counter + 1

    -- Unique email for each request
    local email = string.format("test%d@example.com", counter)

    -- JSON request body
    local body = string.format([[{
        "customer_email": "%s",
        "customer_name": "Test User %d",
        "line_items": [
            {
                "sku_id": "%s",
                "quantity": 1
            }
        ],
        "currency": "USD"
    }]], email, counter, sku_id)

    -- HTTP headers
    local headers = {
        ["Content-Type"] = "application/json",
        ["Accept"] = "application/json"
    }

    return wrk.format("POST", nil, headers, body)
end

-- Statistics tracking
local success_count = 0
local error_count = 0
local sold_out_count = 0

response = function(status, headers, body)
    if status == 201 then
        success_count = success_count + 1
    elseif status == 400 and body:find("sold out") then
        sold_out_count = sold_out_count + 1
    else
        error_count = error_count + 1
    end
end

done = function(summary, latency, requests)
    io.write("\n")
    io.write("----------------------------------------\n")
    io.write("Request Statistics:\n")
    io.write(string.format("  Total Requests:  %d\n", summary.requests))
    io.write(string.format("  Success (201):   %d\n", success_count))
    io.write(string.format("  Sold Out:        %d\n", sold_out_count))
    io.write(string.format("  Errors:          %d\n", error_count))
    io.write("----------------------------------------\n")
end
