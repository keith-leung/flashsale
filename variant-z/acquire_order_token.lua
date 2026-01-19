-- =============================================================================
-- Variant Z: Atomic Token Acquisition Script (FIXED)
-- =============================================================================
--
-- This Lua script executes atomically in Redis to:
-- 1. Acquire a campaign token (if available) using ZPOPMIN
-- 2. Check and decrement SKU inventory
-- 3. Update campaign metadata
--
-- All operations happen in a single atomic transaction, preventing race
-- conditions and ensuring consistency.
--
-- ARGUMENTS:
-- KEYS[1]: Campaign tokens key (campaign:{campaign_id}:tokens)
-- KEYS[2]: SKU inventory key (sku:{sku_id}:inventory)
-- KEYS[3]: Campaign metadata key (campaign:{campaign_id}:metadata)
-- ARGV[1]: Quantity to purchase
-- ARGV[2]: Campaign ID (for metadata update)
--
-- RETURNS:
-- Success: {ok: "ORDER_SUCCESS", remaining_stock: <int>, token: <token_id>}
-- Error: {err: "ERROR_CODE"}
--
-- =============================================================================

-- Extract arguments
local campaign_key = KEYS[1]
local sku_key = KEYS[2]
local metadata_key = KEYS[3]
local quantity = tonumber(ARGV[1])
local campaign_id = ARGV[2]

-- Step 1: Acquire token atomically using ZPOPMIN
-- ZPOPMIN removes and returns the member with the lowest score (FIFO)
local tokens = redis.call('ZPOPMIN', campaign_key, 1)
if not tokens or #tokens == 0 then
    return {err = "TOKEN_NOT_AVAILABLE"}
end

-- Extract token ID from result (ZPOPMIN returns {member, score})
local token = tokens[1]

-- Step 2: Check SKU inventory in cache
local current_stock = redis.call('GET', sku_key)
if not current_stock then
    -- Token acquired but SKU not in cache - restore token
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "SKU_NOT_CACHED"}
end

current_stock = tonumber(current_stock)
if current_stock < quantity then
    -- Token acquired but insufficient stock - restore token
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "INSUFFICIENT_STOCK"}
end

-- Step 3: Decrement SKU inventory
local new_stock = redis.call('DECRBY', sku_key, quantity)

-- Step 4: Update campaign metadata (remaining tokens)
local metadata = redis.call('GET', metadata_key)
if metadata then
    -- Parse JSON metadata
    local cjson = require('cjson')
    local decoded = cjson.decode(metadata)
    decoded.remaining_tokens = decoded.remaining_tokens - 1
    
    -- Update metadata with 60-second TTL
    redis.call('SETEX', metadata_key, 60, cjson.encode(decoded))
end

-- Success - return remaining stock and token
return {ok = "ORDER_SUCCESS", remaining_stock = new_stock, token = token}