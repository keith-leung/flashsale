-- Simple Lua script for verification
local counter = 0
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

request = function()
    counter = counter + 1
    
    local sku_ids = {
        "e9d1807a-f22b-11f0-bbc4-9660160e28bc",
        "e9d1a91c-f22b-11f0-bbc4-9660160e28bc",
        "e9d24e49-f22b-11f0-bbc4-9660160e28bc"
    }
    
    local sku_id = sku_ids[counter % #sku_ids + 1]
    local body = string.format([[{
        "customer_name": "Test User %d",
        "customer_email": "test%d@example.com",
        "line_items": [{"sku_id": "%s", "quantity": 1}]
    }]], counter, counter, sku_id)
    
    return wrk.format(wrk.method, "/orders/", nil, body)
end

function setup(thread)
    thread:set("id", math.random(1, 10000))
end
