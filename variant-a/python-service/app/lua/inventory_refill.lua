-- Adaptive Inventory Refill Script for Flash Sale
-- This Lua script runs atomically in Redis to manage inventory batching
--
-- KEYS[1]: inventory key (e.g., "fs:{campaign_id}:sku:{sku_id}:limit")
-- ARGV[1]: requested batch size (e.g., 500)
-- ARGV[2]: low water mark threshold (e.g., 2000)
--
-- Return codes:
--   -1: Sold out (stock <= 0)
--   -2: Below low water mark - caller should switch to DIRECT mode
--   N > 0: Granted batch size (or remaining stock if less than batch)

local stock = tonumber(redis.call('GET', KEYS[1])) or 0
local batch = tonumber(ARGV[1])
local low_water_mark = tonumber(ARGV[2])

-- Check if sold out
if stock <= 0 then
    return -1  -- SOLD OUT
end

-- Check if below low water mark - signal mode switch
if stock < low_water_mark then
    return -2  -- SWITCH TO DIRECT MODE
end

-- Grant batch if sufficient stock
if stock >= batch then
    redis.call('DECRBY', KEYS[1], batch)
    return batch
else
    -- Grant remainder and set to 0
    local remainder = stock
    redis.call('SET', KEYS[1], 0)
    return remainder
end
