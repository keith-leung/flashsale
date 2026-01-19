-- Lua script for wrk to stress test Variant Zeta (Redis-First)
-- Test URL: http://host:port/orders/ (not /api/v1/orders/)

-- Counter for generating unique emails
local counter = 0

-- Setup method and headers
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- Request function - called for each request
request = function()
    counter = counter + 1

    -- Randomly select 1-3 SKUs for the order
    local num_items = math.random(1, 3)
    local line_items = {}

    -- Predefined SKU IDs (first 5 for rotation)
    local sku_ids = {
        "e9d1807a-f22b-11f0-bbc4-9660160e28bc",
        "e9d1a91c-f22b-11f0-bbc4-9660160e28bc",
        "e9d24e49-f22b-11f0-bbc4-9660160e28bc",
        "e9d1a93a-f22b-11f0-bbc4-9660160e28bc",
        "e9d1a956-f22b-11f0-bbc4-9660160e28bc"
    }

    for i = 1, num_items do
        -- Randomly select a SKU
        local sku_id = sku_ids[math.random(1, #sku_ids)]
        local quantity = math.random(1, 5)  -- Random quantity 1-5

        table.insert(line_items, string.format([[
        {
            "sku_id": "%s",
            "quantity": %d
        }]], sku_id, quantity))
    end

    -- Generate unique customer email using thread ID and counter
    local thread_id = wrk.thread:get("id") or 0
    local customer_email = string.format("stress-test-%d-%d@example.com", thread_id, counter)

    -- Build request body
    local body = string.format([[{
        "customer_name": "Stress Test User %d",
        "customer_email": "%s",
        "line_items": [%s]
    }]], counter, customer_email, table.concat(line_items, ","))

    -- Return formatted request (VARIANT ZETA: /orders/ not /api/v1/orders/)
    return wrk.format(wrk.method, "/orders/", nil, body)
end

-- Initialize thread with counters
function setup(thread)
    thread:set("id", math.random(1, 10000))
end

-- Print initialization message
print(string.format("Loaded %d SKU IDs for stress testing", 5))
print("Variant Zeta: Redis-First Architecture")
print("Endpoint: /orders/")
print("Features:")
print("  - Atomic Lua script inventory reservation")
print("  - Zero database reads during flash sale")
print("  - Redis metadata caching")
print("  - Async batch persistence to database")
