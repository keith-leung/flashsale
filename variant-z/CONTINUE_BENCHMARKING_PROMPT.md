# Task: Build and Benchmark Variant Z C# and Java Implementations

## Context

Variant Z (Token Pre-Allocation with Synchronous Persistence) has been successfully implemented in Python and benchmarked. The Python implementation demonstrates:

- **Average Latency**: 14.12ms
- **Throughput**: ~1,500-2,000 req/s (projected concurrent)
- **Error Rate**: 0%
- **Architecture**: Redis token acquisition + Synchronous database persistence

We need to implement the same Variant Z architecture in C# and Java, then benchmark all three implementations for comprehensive comparison.

## Architecture Requirements

All implementations must follow the **exact same Variant Z architecture**:

### Core Components

1. **Token Pre-Allocation System (Redis)**
   - Pre-allocate tokens for campaigns in Redis sorted sets
   - Use atomic Lua scripts for token acquisition (ZPOPMIN)
   - Token buckets: `token:{campaign_id}` (sorted set by token value)
   - SKU inventory cache: `sku:inventory:{sku_id}` (string)

2. **Order Creation Flow**
   ```
   Request → Check SKU Campaign → Token Acquisition (Redis) → 
   Database Persistence (Synchronous) → Return Response
   ```

3. **Synchronous Database Persistence**
   - Create order (status="pending")
   - Create order line items
   - Create payment record
   - Update inventory (decrement quantity)
   - Update campaign sold quantity
   - Commit transaction before returning HTTP 201

### Lua Script (Token Acquisition)

Must use this exact Lua script (or equivalent logic):

```lua
-- acquire_order_token.lua
local campaign_id = KEYS[1]
local sku_id = KEYS[2]
local quantity = tonumber(ARGV[1])

-- Check token availability
local token = redis.call('ZPOPMIN', 'token:' .. campaign_id)
if not token then
    return {err = 'TOKEN_NOT_AVAILABLE'}
end

-- Check SKU inventory
local inventory_key = 'sku:inventory:' .. sku_id
local inventory = tonumber(redis.call('GET', inventory_key) or 0)
if inventory < quantity then
    -- Return token (rollback)
    redis.call('ZADD', 'token:' .. campaign_id, token, token)
    return {err = 'INSUFFICIENT_STOCK', remaining_stock = inventory}
end

-- Decrement inventory
redis.call('DECRBY', inventory_key, quantity)

-- Update metadata
local now = tonumber(redis.call('TIME')[1])
redis.call('HINCRBY', 'campaign:' .. campaign_id, 'sold_quantity', quantity)

return {token = token, campaign_id = campaign_id, sku_id = sku_id, quantity = quantity, timestamp = now}
```

## Implementation Tasks

### Task 1: Build C# Implementation (Variant Z)

**Location**: `variant-z/csharp-service/`

**Requirements**:

1. **Token Manager**
   - Create `Core/TokenManager.cs`
   - Implement `AllocateCampaignTokensAsync(campaign_id, count)`
   - Implement `AcquireTokenAsync(campaign_id, sku_id, quantity)` using Lua script
   - Handle Redis connection and Lua script execution

2. **Order Service**
   - Modify `Services/OrderService.cs`
   - Add token acquisition logic before database operations
   - Keep synchronous database persistence
   - Change order status to `Status.Pending` (not `Created`)

3. **Database Models**
   - Ensure `Order` entity uses `Status.Pending`
   - Add `FlashSaleCampaignId` property if missing
   - Update SKU inventory tracking

4. **Lua Script**
   - Add `acquire_order_token.lua` to project
   - Configure loading on startup

5. **Configuration**
   - Update `appsettings.json` with Redis connection
   - Ensure MariaDB connection string is correct

**Reference**: Use Python implementation at `variant-z/python-service/app/core/token_manager.py` as reference

### Task 2: Build Java Implementation (Variant Z)

**Location**: `variant-z/java-service/src/main/java/com/flashsale/`

**Requirements**:

1. **Token Manager**
   - Create `core/TokenManager.java`
   - Implement `allocateCampaignTokens(String campaignId, int count)`
   - Implement `acquireToken(String campaignId, String skuId, int quantity)` using Lua script
   - Use RedisTemplate for Redis operations
   - Handle DefaultRedisScriptException

2. **Order Service**
   - Modify `service/OrderService.java`
   - Add token acquisition logic before database operations
   - Keep synchronous database persistence
   - Change order status to `PENDING` (not `CREATED`)

3. **Database Entities**
   - Ensure `Order` entity uses `OrderStatus.PENDING`
   - Add `flashSaleCampaignId` field if missing
   - Update SKU inventory tracking

4. **Lua Script**
   - Add `acquire_order_token.lua` to `resources/`
   - Configure loading using `DefaultRedisScript`

5. **Configuration**
   - Update `application.yml` with Redis configuration
   - Ensure MariaDB datasource is correct

**Reference**: Use Python implementation at `variant-z/python-service/app/core/token_manager.py` as reference

### Task 3: Test Data Initialization

For each implementation (C# and Java), ensure:

1. **Campaign exists** in database:
   - Campaign ID: `e26bb7d0-c863-4cd6-b08c-44fcca0a8c28`
   - SKU ID: `2c2e23fa-f47b-4884-9b45-bf2a640f1ff3`
   - Status: Active

2. **Tokens allocated** in Redis:
   - 9,847 tokens for the campaign
   - Use `token_manager.allocate_tokens()` method

3. **SKU inventory cached** in Redis:
   - 10,000 units for benchmark SKU
   - Use `redis_client.cache_sku_inventory()` method

### Task 4: Verification

Before benchmarking, verify each implementation:

1. **Health Check**
   ```bash
   curl http://localhost:8002/health  # C#
   curl http://localhost:8003/health  # Java
   ```

2. **Single Order Test**
   ```bash
   curl -X POST http://localhost:8002/api/v1/orders/ \
     -H "Content-Type: application/json" \
     -d '{
       "customer_name": "Test",
       "customer_email": "test@example.com",
       "line_items": [{
         "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
         "quantity": 1
       }]
     }'
   ```

3. **Token System Check**
   ```bash
   docker exec flash-redis-z redis-cli ZCARD token:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28
   # Should return: 9847 (or slightly less after test orders)
   ```

### Task 5: Benchmarking

Run identical benchmarks on all three implementations:

#### Python (Port 8001)
```bash
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:8001/api/v1/orders/
```

#### C# (Port 8002)
```bash
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:8002/api/v1/orders/
```

#### Java (Port 8003)
```bash
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:8003/api/v1/orders/
```

Run tests with multiple concurrency levels: [10, 20, 50, 100]

### Task 6: Collect and Document Results

For each implementation, record:

1. **Throughput** (requests per second)
2. **Average Latency** (milliseconds)
3. **P95/P99 Latency**
4. **Error Rate** (percentage)
5. **Total Orders Created**

Create comparison table:

| Metric | Python | C# | Java | Best |
|--------|---------|-----|------|------|
| Avg Latency | 14.12ms | ? | ? | ? |
| P95 Latency | ~20ms | ? | ? | ? |
| Throughput | ~1,800 req/s | ? | ? | ? |
| Error Rate | 0% | ? | ? | ? |
| Max Concurrency | 100 | ? | ? | ? |

### Task 7: Analysis

Analyze results to answer:

1. **Performance Ranking**: Which language performs best?
2. **Latency Variance**: Is C#/Java more consistent than Python?
3. **Scalability**: Which handles higher concurrency better?
4. **Resource Usage**: CPU/memory comparison
5. **Code Complexity**: Which is easiest to maintain?

## Expected Outcomes

1. ✅ C# and Java implementations working with token pre-allocation
2. ✅ All three services using same Redis token system
3. ✅ Synchronous database persistence in all implementations
4. ✅ Comparable benchmark results across languages
5. ✅ Comprehensive comparison report with recommendations

## Files to Create/Modify

### C#
- `variant-z/csharp-service/Core/TokenManager.cs` (NEW)
- `variant-z/csharp-service/Services/OrderService.cs` (MODIFY)
- `variant-z/csharp-service/Models/Order.cs` (MODIFY)
- `variant-z/csharp-service/acquire_order_token.lua` (NEW)
- `variant-z/csharp-service/Program.cs` (MODIFY - add Redis)

### Java
- `variant-z/java-service/src/main/java/com/flashsale/core/TokenManager.java` (NEW)
- `variant-z/java-service/src/main/java/com/flashsale/service/OrderService.java` (MODIFY)
- `variant-z/java-service/src/main/java/com/flashsale/entity/Order.java` (MODIFY)
- `variant-z/java-service/src/main/resources/acquire_order_token.lua` (NEW)
- `variant-z/java-service/src/main/resources/application.yml` (MODIFY - add Redis)

### Benchmark Scripts
- `variant-z/benchmark_all_languages.sh` (NEW - runs all three)
- `benchmark_results/VARIANT_Z_CSHARP_RESULTS.md` (NEW)
- `benchmark_results/VARIANT_Z_JAVA_RESULTS.md` (NEW)
- `benchmark_results/VARIANT_Z_LANGUAGE_COMPARISON.md` (NEW)

## Success Criteria

1. Token acquisition works in all three languages
2. Order creation succeeds with HTTP 201 in all implementations
3. Zero errors during benchmarking
4. Performance metrics are comparable and reasonable
5. Comprehensive comparison report is generated
6. Recommendations are provided for production deployment

## Notes

- All implementations must share the same Redis instance
- All implementations must write to the same MariaDB database
- Benchmark tests must be identical across all languages
- Use the same SKU and campaign IDs for fair comparison
- Document any language-specific optimizations applied

## Reference Implementation

Use Python implementation as reference:
- Token Manager: `variant-z/python-service/app/core/token_manager.py`
- Order Endpoint: `variant-z/python-service/app/api/endpoints/orders.py`
- Redis Client: `variant-z/python-service/app/core/redis.py`
- Lua Script: `variant-z/acquire_order_token.lua`

## Next Steps After Completion

1. Create production deployment guide
2. Generate performance optimization recommendations
3. Document best practices for each language
4. Create monitoring and alerting setup guide
5. Write comparison whitepaper for architectural decisions

---

**Objective**: Build complete Variant Z implementation in C# and Java, then benchmark all three languages to determine optimal implementation for production deployment.