-- Atomic inventory reservation with campaign limit enforcement
-- Variant Zeta - Redis-First Architecture

-- KEYS
-- KEYS[1]: campaign:{spu_id} (campaign hash)
-- KEYS[2]: sku:{sku_id}:stock (inventory integer)

-- ARGV
-- ARGV[1]: spu_id (string)
-- ARGV[2]: sku_id (string)
-- ARGV[3]: quantity (integer)
-- ARGV[4]: order_id (string)
-- ARGV[5]: worker_index (integer, 0-4)
-- ARGV[6]: current_timestamp (integer)

local campaign_key = KEYS[1]
local stock_key = KEYS[2]
local spu_id = ARGV[1]
local sku_id = ARGV[2]
local quantity = tonumber(ARGV[3])
local order_id = ARGV[4]
local worker_index = ARGV[5]
local current_timestamp = tonumber(ARGV[6])

-- Check if campaign exists
local campaign_exists = redis.call('EXISTS', campaign_key)
if campaign_exists == 0 then
    return {err = "CAMPAIGN_NOT_FOUND"}
end

-- Get campaign data
local campaign = redis.call('HGETALL', campaign_key)
if #campaign == 0 then
    return {err = "CAMPAIGN_NOT_FOUND"}
end

-- Parse campaign hash
local campaign_data = {}
for i = 1, #campaign, 2 do
    campaign_data[campaign[i]] = campaign[i + 1]
end

-- Check if campaign is active
if campaign_data['is_active'] ~= 'true' and campaign_data['is_active'] ~= '1' then
    return {err = "CAMPAIGN_NOT_ACTIVE"}
end

-- Check campaign time window
local start_time = tonumber(campaign_data['start_time'])
local end_time = tonumber(campaign_data['end_time'])
if current_timestamp < start_time or current_timestamp > end_time then
    return {err = "CAMPAIGN_NOT_IN_TIME_WINDOW"}
end

-- Check campaign limit
local total_limit = tonumber(campaign_data['total_sale_limit'])
local sold = tonumber(campaign_data['sold_quantity'])
if not sold then
    sold = 0
end

if sold + quantity > total_limit then
    return {
        err = "CAMPAIGN_LIMIT_REACHED",
        sold = sold,
        total = total_limit,
        available = total_limit - sold
    }
end

-- Check if stock key exists
local stock_exists = redis.call('EXISTS', stock_key)
if stock_exists == 0 then
    return {err = "STOCK_NOT_FOUND"}
end

-- Get current stock
local stock = redis.call('GET', stock_key)
if not stock then
    return {err = "STOCK_NOT_FOUND"}
end
stock = tonumber(stock)

-- Check if sufficient stock
if stock < quantity then
    return {
        err = "INSUFFICIENT_STOCK",
        available = stock,
        requested = quantity
    }
end

-- Atomic operations
-- 1. Increment campaign sold quantity
redis.call('HINCRBY', campaign_key, 'sold_quantity', quantity)

-- 2. Decrement stock
redis.call('DECRBY', stock_key, quantity)

-- 3. Enqueue to worker queue
local queue_key = 'order_queue:' .. spu_id .. ':worker_' .. worker_index
redis.call('LPUSH', queue_key, order_id)

-- 4. Set order status with TTL
redis.call('SETEX', 'order:' .. order_id .. ':status', 3600, 'pending')

-- Return success
return {
    success = true,
    remaining_stock = stock - quantity,
    remaining_campaign = total_limit - (sold + quantity),
    queue_key = queue_key
}
