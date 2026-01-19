-- Lua script for wrk to send order creation requests (Variant Z - Workable)
-- FIXED: Add trailing slash to avoid 307 redirect

-- Load SKU IDs from file
local sku_ids = {}
local file = io.open("/tmp/stress_test_sku_ids.txt", "r")
if file then
    for line in file:lines() do
        table.insert(sku_ids, line)
    end
    file:close()
else
    print("ERROR: Could not open /tmp/stress_test_sku_ids.txt")
    os.exit(1)
end

print(string.format("Loaded %d SKU IDs for stress testing", #sku_ids))

-- Counter for generating unique emails
local counter = 0

-- Setup method and headers
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- Request function
request = function()
    counter = counter + 1

    -- Randomly select 1-3 SKUs for order
    local num_items = math.random(1, 3)
    local line_items = {}

    for i = 1, num_items do
        local sku_id = sku_ids[math.random(1, #sku_ids)]
        local quantity = math.random(1, 5)

        table.insert(line_items, string.format([[
        {
            "sku_id": "%s",
            "quantity": %d
        }]], sku_id, quantity))
    end

    -- Generate unique customer email
    local thread_id = wrk.thread:get("id") or 0
    local customer_email = string.format("stress-test-%d-%d@example.com", thread_id, counter)

    -- Build request body
    local body = string.format([[{
        "customer_name": "Stress Test User %d",
        "customer_email": "%s",
        "line_items": [%s]
    }]], counter, customer_email, table.concat(line_items, ","))

    -- FIXED: Add trailing slash to avoid redirect
    return wrk.format(wrk.method, "/api/v1/orders/", nil, body)
end

-- Initialize thread
function setup(thread)
    thread:set("id", math.random(1, 10000))
end
