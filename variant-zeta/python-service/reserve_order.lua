-- =============================================================================
-- Variant Zeta: Atomic Order Reservation Script (BUG-FREE)
-- =============================================================================

local campaign_key = KEYS[1]
local stock_key = KEYS[2]
local quantity = tonumber(ARGV[1])

-- HGETALL returns flat array: [key1, value1, key2, value2, ...]
local campaign_data = redis.call('HGETALL', campaign_key)

-- Parse into table
local campaign = {}
for i = 1, #campaign_data, 2 do
    campaign[campaign_data[i]] = campaign_data[i + 1]
end

local sold_quantity = tonumber(campaign['sold_quantity'] or 0)
local total_sale_limit = tonumber(campaign['total_sale_limit'] or 0)

-- Check campaign limit
if sold_quantity + quantity > total_sale_limit then
    -- Return flat array for parsing: ['err', 'ERROR_CODE', 'remaining', VALUE]
    return {'err', 'CAMPAIGN_LIMIT_EXCEEDED', 'remaining', total_sale_limit - sold_quantity}
end

-- Check SKU inventory
local current_stock = tonumber(redis.call('GET', stock_key) or 0)

if current_stock < quantity then
    -- Return flat array for parsing: ['err', 'ERROR_CODE', 'available', VALUE]
    return {'err', 'INSUFFICIENT_STOCK', 'available', current_stock}
end

-- Atomically decrement inventory and increment campaign sold
redis.call('DECRBY', stock_key, quantity)
redis.call('HINCRBY', campaign_key, 'sold_quantity', quantity)

-- Return flat array for parsing: ['ok', 'STATUS', 'remaining_stock', VALUE]
return {'ok', 'RESERVED', 'remaining_stock', current_stock - quantity}
