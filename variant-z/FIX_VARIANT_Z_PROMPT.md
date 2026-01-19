# Task: Fix Variant Z Token Pre-Allocation System and Run Benchmark

## Context

Variant Z's token pre-allocation system is completely broken. The benchmark investigation revealed:

1. **Redis Token Acquisition Fails**: All order creation attempts return "Token acquisition error: REDIS_ERROR"
2. **No Available Tokens**: Campaigns are either sold out or not initialized in Redis
3. **Cannot Create Orders**: Zero orders created across all benchmark attempts

## Root Cause

Variant Z requires token pre-allocation in Redis before orders can be created:

```python
# From variant-z/python-service/app/api/endpoints/orders.py:70-91
campaign = await _get_active_campaign_for_sku(db, sku.spu_id)

if campaign:
    # Variant Z path: Use token pre-allocation
    token_result = await token_manager.acquire_token(
        campaign_id=campaign.id,
        sku_id=sku_id,
        quantity=quantity
    )
```

## Tasks to Complete

### Task 1: Diagnose Redis Token System

1. **Check Redis Connection**
   ```bash
   docker exec flash-redis-z redis-cli PING
   docker exec flash-redis-z redis-cli KEYS "token:*"
   docker exec flash-redis-z redis-cli KEYS "campaign:*"
   ```

2. **Check Lua Scripts**
   ```bash
   docker exec flash-redis-z redis-cli SCRIPT LIST
   ```

3. **Review Token Manager Implementation**
   - Read `variant-z/python-service/app/core/token_manager.py`
   - Identify why token acquisition returns `REDIS_ERROR`
   - Check if Lua scripts are properly loaded

### Task 2: Initialize Campaign Tokens

1. **Create Token Allocation Script**
   - Create a script to initialize tokens for existing campaigns
   - Use `token_manager.allocate_tokens()` method
   - Allocate sufficient tokens for benchmarking (e.g., 10,000 tokens)

2. **Verify Token Allocation**
   - Check Redis for token keys
   - Verify token counts
   - Test token acquisition manually

### Task 3: Fix Token Acquisition Issues

Based on diagnosis, fix any issues found:

1. **If Lua scripts not loaded**: Load them properly
2. **If Redis connection issues**: Fix connection configuration
3. **If token buckets not created**: Create them during initialization
4. **If campaign data missing**: Ensure campaigns exist in database

### Task 4: Create Test Data

1. **Create Test SKU with Available Tokens**
   - Either use existing SKU with allocated tokens
   - Or create new SKU that doesn't belong to a campaign (to test Variant Y path)

2. **Update Benchmark Script**
   - Update `variant-z/wrk_order_script.lua` with valid SKU ID
   - Ensure SKU has available tokens

### Task 5: Run Corrected Benchmark

1. **Run the benchmark script**
   ```bash
   cd /home/syracuse/flashsale
   bash variant-z/benchmark_python_orders_corrected.sh
   ```

2. **Verify Results**
   - Check that orders are actually created in database
   - Verify Little's Law validation passes
   - Ensure error rate is 0%

3. **Document Results**
   - Create summary of actual performance
   - Compare with Variant Y baseline
   - Note any remaining issues

## Expected Outcome

After completing these tasks:

1. ✅ Redis token system is functional
2. ✅ Campaigns have available tokens
3. ✅ Orders can be created successfully
4. ✅ Benchmark completes with valid results
5. ✅ Little's Law validation passes
6. ✅ Database operations are confirmed

## Files to Review

- `variant-z/python-service/app/core/token_manager.py` - Token management logic
- `variant-z/python-service/app/core/redis.py` - Redis client and Lua scripts
- `variant-z/python-service/app/api/endpoints/orders.py` - Order creation flow
- `variant-z/benchmark_python_orders_corrected.sh` - Benchmark script
- `variant-z/wrk_order_script.lua` - wrk test script

## Current Database State

- Orders: 5,603 (from previous tests)
- SKUs available:
  - `2c2e23fa-f47b-4884-9b45-bf2a640f1ff3` (FS-TEST-BENCHMARK-001) - Sold out
  - `bec6227c-9d2e-4e8f-a16b-fc090d074b16` (FS-TEST-001) - Redis error

## Success Criteria

1. Token acquisition succeeds without errors
2. Benchmark creates orders in database
3. Throughput is within Little's Law limits
4. Error rate is 0%
5. Results are reproducible

## Notes

- The benchmark script is already fixed and ready to use
- The wrk script needs a valid SKU ID with available tokens
- Focus on fixing the token pre-allocation system first
- Verify each step before proceeding to the next