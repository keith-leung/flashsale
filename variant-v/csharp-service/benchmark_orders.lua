-- benchmark_orders.lua - Lua script for wrk

wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

-- SKU IDs (hardcoded for test)
local sku_ids = {
    "sku-001", "sku-002", "sku-003", "sku-004", "sku-005", "sku-006"
}

-- Campaign ID
local campaign_id = "test-flash-campaign-001"

request = function()
    local sku_id = sku_ids[math.random(#sku_ids)]
    local quantity = 1
    local price = 49.99
    local email = "test" .. math.random(100000) .. "@example.com"
    
    local body = string.format(
        '{"customerEmail": "%s", "skuId": "%s", "quantity": %d, "unitPrice": %f, "flashSaleCampaignId": "%s"}',
        email, sku_id, quantity, price, campaign_id
    )
    
    return wrk.format(nil, nil, nil, body)
end
