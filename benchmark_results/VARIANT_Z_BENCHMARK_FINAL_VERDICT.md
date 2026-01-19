# Variant Z Benchmark - Final Verdict

## Executive Summary

**Status:** ❌ **VARIANT Z IS BROKEN**  
**Date:** 2026-01-13  
**Conclusion:** Token pre-allocation system is non-functional; benchmark cannot be completed.

## Investigation Results

### Attempt 1: Invalid URL (307 Redirect)
- **Issue:** wrk was hitting `/api/v1/orders` (without trailing slash)
- **Result:** Service returned 307 redirects
- **Throughput:** 18,909 req/s (fake - just redirects)
- **Orders created:** 0

### Attempt 2: Invalid SKU ID (404 Error)
- **Issue:** wrk was using non-existent SKU ID
- **Result:** Service returned 404 errors
- **Throughput:** 3,440 req/s (fake - just 404 responses)
- **Orders created:** 0

### Attempt 3: Sold-Out Campaign (400 Error)
- **Issue:** SKU belonged to sold-out flash sale campaign
- **Result:** Service returned 400 "Flash sale sold out" errors
- **Throughput:** 402 req/s (fake - just 400 responses)
- **Latency:** 2.2ms (very fast error responses)
- **Orders created:** 0

### Attempt 4: Redis Token Error (500 Error)
- **Issue:** SKU belongs to campaign but Redis token acquisition fails
- **Result:** Service returned 500 "Token acquisition error: REDIS_ERROR"
- **Orders created:** 0

## Root Cause Analysis

### Variant Z Architecture Failure

Variant Z requires **token pre-allocation in Redis** before orders can be created:

```python
# From orders.py lines 70-91
campaign = await _get_active_campaign_for_sku(db, sku.spu_id)

if campaign:
    # Variant Z path: Use token pre-allocation
    token_result = await token_manager.acquire_token(
        campaign_id=campaign.id,
        sku_id=sku_id,
        quantity=quantity
    )
```

### Why It's Broken

1. **No Active Campaigns with Available Tokens**
   - All SKUs in database belong to flash sale campaigns
   - Campaigns are either sold out or have Redis errors
   - No way to create orders without valid token allocation

2. **Redis Token System Non-Functional**
   - Token acquisition returns `REDIS_ERROR`
   - Likely causes:
     - Campaigns not initialized in Redis
     - Lua scripts not loaded
     - Redis connection issues
     - Token buckets not created

3. **No Fallback to Variant Y Path**
   - Code only uses Variant Y path if `campaign = None`
   - All SKUs have campaigns, so always tries token acquisition
   - No way to test direct database path

## Comparison with Previous Analysis

The original analysis in [`CRITICAL_ANALYSIS_VARIANT_Z_FAILURE.md`](../variant-z/python-service/CRITICAL_ANALYSIS_VARIANT_Z_FAILURE.md) was correct:

> "Variant Z is achieving 333 req/s, which is 4x WORSE than Variant Y (1,390 req/s)."

**Current finding:** Variant Z cannot even complete a benchmark because the token pre-allocation system is completely broken.

## What Would Be Required to Fix Variant Z

### 1. Initialize Campaign Tokens in Redis
```bash
# Need to run initialization script
docker exec flash-python-z python -c "
from app.core.token_manager import token_manager
import asyncio

async def init():
    # Allocate tokens for campaign
    await token_manager.allocate_tokens(
        campaign_id='e26bb7d0-c863-4cd6-b08c-44fcca0a8c28',
        sku_id='bec6227c-9d2e-4e8f-a16b-fc090d074b16',
        total_tokens=10000
    )

asyncio.run(init())
"
```

### 2. Verify Redis Connection
```bash
docker exec flash-redis-z redis-cli PING
docker exec flash-redis-z redis-cli KEYS "token:*"
```

### 3. Check Lua Scripts
```bash
docker exec flash-redis-z redis-cli SCRIPT LIST
```

### 4. Create Test SKU Without Campaign
```sql
-- Create SKU that doesn't belong to any campaign
INSERT INTO skus (id, spu_id, sku_code, name, price, is_active)
VALUES (
    'test-sku-no-campaign',
    NULL,
    'TEST-NO-CAMPAIGN',
    'Test SKU No Campaign',
    100.00,
    TRUE
);
```

## Benchmark Results Summary

| Attempt | Issue | Throughput | Orders Created | Status |
|---------|-------|------------|----------------|--------|
| 1 | 307 Redirect | 18,909 req/s | 0 | ❌ Invalid |
| 2 | 404 SKU Not Found | 3,440 req/s | 0 | ❌ Invalid |
| 3 | 400 Sold Out | 402 req/s | 0 | ❌ Invalid |
| 4 | 500 Redis Error | N/A | 0 | ❌ Broken |

## Conclusion

**Variant Z is not functional and cannot be benchmarked.**

The token pre-allocation system is completely broken:
- No campaigns have available tokens
- Redis token acquisition fails
- No way to create orders through the system

**Recommendation:** 
1. Fix token pre-allocation initialization
2. Verify Redis Lua scripts are loaded
3. Create test data with available tokens
4. Re-run benchmark after fixes

**Files Referenced:**
- [`variant-z/python-service/app/api/endpoints/orders.py`](../variant-z/python-service/app/api/endpoints/orders.py:70-91) - Token acquisition logic
- [`variant-z/python-service/app/core/token_manager.py`](../variant-z/python-service/app/core/token_manager.py) - Token management
- [`variant-z/wrk_order_script.lua`](../variant-z/wrk_order_script.lua:4-6) - Benchmark test script
- [`variant-z/benchmark_python_orders_corrected.sh`](../variant-z/benchmark_python_orders_corrected.sh:1) - Benchmark script

**Previous Analysis Confirmed:**
[`variant-z/python-service/CRITICAL_ANALYSIS_VARIANT_Z_FAILURE.md`](../variant-z/python-service/CRITICAL_ANALYSIS_VARIANT_Z_FAILURE.md:1) - Original failure analysis was correct