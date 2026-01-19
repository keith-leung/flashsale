-- KEYS[1]: campaign tokens key (campaign:{id}:tokens)
-- KEYS[2]: SKU inventory key (sku:{sku_id}:inventory)
-- KEYS[3]: Campaign metadata key (campaign:{id}:metadata)
-- ARGV[1]: Quantity to purchase
-- ARGV[2]: Campaign ID

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

-- Extract token ID from result
local token = tokens[1]

-- Step 2: Check and decrement SKU inventory
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

-- Decrement inventory
redis.call('DECRBY', sku_key, quantity)

-- Update campaign metadata
local metadata = redis.call('GET', metadata_key)
if metadata then
    local decoded = cjson.decode(metadata)
    decoded.remaining_tokens = decoded.remaining_tokens - 1
    redis.call('SETEX', metadata_key, 60, cjson.encode(decoded))
end

return {ok = "ORDER_SUCCESS", remaining_stock = current_stock - quantity}