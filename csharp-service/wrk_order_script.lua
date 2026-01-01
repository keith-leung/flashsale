-- Lua script for wrk to send order creation requests
-- This script randomly selects SKUs and creates order requests

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
    print("Please run: python setup_test_data.py")
    os.exit(1)
end

-- Verify we have SKU IDs
if #sku_ids == 0 then
    print("ERROR: No SKU IDs found in /tmp/stress_test_sku_ids.txt")
    print("Please run: python setup_test_data.py")
    os.exit(1)
end

print(string.format("Loaded %d SKU IDs for stress testing", #sku_ids))

-- Counter for generating unique emails (thread-safe using wrk.thread.id)
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
        "customer_email": "%s",
        "customer_name": "Stress Test User %d",
        "currency": "USD",
        "line_items": [%s]
    }]], customer_email, counter, table.concat(line_items, ","))

    return wrk.format(wrk.method, nil, nil, body)
end

-- Initialize thread with counters
function setup(thread)
    thread:set("id", math.random(1, 10000))
end

-- Initialize per-thread counters
function init(args)
    success_count = 0
    error_count = 0
    error_codes = {}
end

-- Response function - track errors
response = function(status, headers, body)
    if status == 200 or status == 201 then
        success_count = success_count + 1
    else
        error_count = error_count + 1
        error_codes[status] = (error_codes[status] or 0) + 1
    end
end