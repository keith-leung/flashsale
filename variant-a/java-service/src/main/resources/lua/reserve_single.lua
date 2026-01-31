-- Atomic Single-Item Reservation Script for Flash Sale
-- This Lua script runs atomically in Redis for direct-mode reservations
--
-- KEYS[1]: pool key (e.g., "fs:{campaign_id}:redis_pool:sku:{sku_id}")
-- ARGV[1]: quantity to reserve (default 1)
--
-- Return codes:
--   -1: Insufficient stock (no modification made)
--   N >= 0: New stock value after decrement (success)
--
-- IMPORTANT: This script NEVER goes negative. Zero overselling guaranteed.

local stock = tonumber(redis.call('GET', KEYS[1])) or 0
local qty = tonumber(ARGV[1]) or 1

-- Atomic check-and-decrement
if stock >= qty then
    return redis.call('DECRBY', KEYS[1], qty)
else
    return -1  -- Insufficient stock, NO modification
end
