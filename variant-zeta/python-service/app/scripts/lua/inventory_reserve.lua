-- Redis Lua script for atomic inventory reservation (Variant Zeta)

local sku_key = KEYS[1]
local queue_key = KEYS[2]
local sku_id = ARGV[1]
local quantity = tonumber(ARGV[2])
local order_id = ARGV[3]

-- Check if stock exists
local exists = redis.call('EXISTS', sku_key)
if exists == 0 then
    return {err = "SKU_NOT_FOUND"}
end

-- Check stock availability
local available = redis.call('HGET', sku_key, 'available')
if not available then
    return {err = "SKU_NOT_FOUND"}
end
available = tonumber(available)

if available < quantity then
    return {err = "INSUFFICIENT_STOCK", available = available}
end

-- Atomic reservation
redis.call('HINCRBY', sku_key, 'available', -quantity)
redis.call('HINCRBY', sku_key, 'reserved', quantity)

-- Add to persistence queue
redis.call('LPUSH', queue_key, order_id)

-- Set initial order status
redis.call('SET', 'order:' .. order_id .. ':status', 'pending')

-- Return success with remaining stock
return {success = true, remaining = available - quantity}
