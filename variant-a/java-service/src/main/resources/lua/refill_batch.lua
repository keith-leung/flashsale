-- Atomic Batch Refill Script for Flash Sale
-- This Lua script runs atomically in Redis to refill local cache
--
-- KEYS[1]: pool key (e.g., "fs:{campaign_id}:redis_pool:spu_counter" or "fs:{campaign_id}:redis_pool:sku:{sku_id}")
-- ARGV[1]: requested batch size (e.g., 500)
--
-- Return codes:
--   -1: Pool exhausted (stock <= 0)
--   N >= 0: Granted amount (batch_size or remainder if less available)
--
-- IMPORTANT: This script NEVER goes negative. If insufficient stock, it returns -1 without modifying.

local stock = tonumber(redis.call('GET', KEYS[1])) or 0
local batch = tonumber(ARGV[1])

-- Check if pool is exhausted
if stock <= 0 then
    return -1  -- EXHAUSTED
end

-- Grant what's available (up to batch size)
if stock >= batch then
    -- Full batch available
    redis.call('DECRBY', KEYS[1], batch)
    return batch
else
    -- Partial batch - grant remainder
    local granted = stock
    redis.call('SET', KEYS[1], 0)
    return granted
end
