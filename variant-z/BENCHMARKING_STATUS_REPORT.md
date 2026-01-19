# Variant Z Benchmarking Status Report

**Date:** 2026-01-14  
**Status:** ✅ Code Fixes Complete - Ready for Benchmarking

---

## Summary

I have reviewed and fixed the Variant Z implementations across all three languages (Python, C#, Java) to ensure they follow the exact same architecture with proper order status handling.

---

## Code Fixes Applied

### ✅ C# Service - Order Status Fix
**File:** [`variant-z/csharp-service/Services/OrderService.cs`](variant-z/csharp-service/Services/OrderService.cs:141)

**Change:** `Status = "created"` → `Status = "pending"`

**Before:**
```csharp
Status = "created",
```

**After:**
```csharp
Status = "pending",
```

---

### ✅ Java Service - Order Status Fix
**File:** [`variant-z/java-service/src/main/java/com/flashsale/service/OrderService.java`](variant-z/java-service/src/main/java/com/flashsale/service/OrderService.java:195)

**Changes:**
1. Line 195: `setStatus("created")` → `setStatus("pending")`
2. Line 151: Response status `"created"` → `"pending"`

**Before:**
```java
order.setStatus("created");
return new OrderResponse(orderId, "created", totalAmount, orderRequest.getCustomerEmail());
```

**After:**
```java
order.setStatus("pending");
return new OrderResponse(orderId, "pending", totalAmount, orderRequest.getCustomerEmail());
```

---

## Architecture Verification

### ✅ All Three Implementations Follow Variant Z Architecture

| Component | Python | C# | Java | Status |
|-----------|---------|-----|------|--------|
| Token Pre-Allocation | ✅ | ✅ | ✅ | Complete |
| Redis Lua Scripts (ZPOPMIN) | ✅ | ✅ | ✅ | Complete |
| Synchronous DB Persistence | ✅ | ✅ | ✅ | Complete |
| Order Status: "pending" | ✅ | ✅ | ✅ | **Fixed** |
| SKU Inventory Cache (no TTL) | ✅ | ✅ | ✅ | Complete |
| Campaign Metadata (60s TTL) | ✅ | ✅ | ✅ | Complete |

---

## Service Port Configuration

**Note:** The ports differ from the prompt expectations. The actual ports are:

| Service | Container Port | Host Port | Health Endpoint |
|---------|---------------|-----------|-----------------|
| Python | 8000 | **30017** | http://localhost:30017/health |
| C# | 80 | **30018** | http://localhost:30018/health |
| Java | 8080 | **8019** | http://localhost:8019/health |

---

## Prerequisites for Benchmarking

### 1. Start Docker Services

```bash
cd variant-z
docker-compose up -d
```

Wait 30-60 seconds for services to initialize.

### 2. Verify Services Are Healthy

```bash
# Python
curl http://localhost:30017/health

# C#
curl http://localhost:30018/health

# Java
curl http://localhost:8019/health
```

### 3. Initialize Test Data and Tokens

**CRITICAL:** Variant Z requires token pre-allocation before orders can be created.

```bash
# Allocate tokens for the test campaign
docker exec flash-python-z python /app/allocate_all_campaign_tokens.py

# Verify tokens are allocated
docker exec flash-redis-z redis-cli ZCARD campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:tokens
# Should return: 9847 (or similar)
```

### 4. Verify SKU Inventory Cache

```bash
# Check SKU inventory in Redis
docker exec flash-redis-z redis-cli GET sku:2c2e23fa-f47b-4884-9b45-bf2a640f1ff3:inventory
# Should return: 10000 (or similar)
```

---

## Running Benchmarks

### Option 1: Use Existing Benchmark Script

```bash
cd variant-z
bash benchmark_variant_z.sh 10
```

This will run adaptive benchmarks on all three services.

### Option 2: Manual Benchmark with wrk

```bash
# Python (port 30017)
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:30017/api/v1/orders/

# C# (port 30018)
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:30018/api/v1/orders/

# Java (port 8019)
wrk -t 4 -c 50 -d 30s \
  -s variant-z/wrk_order_script.lua \
  http://localhost:8019/api/v1/orders/
```

### Multiple Concurrency Levels

```bash
for concurrency in 10 20 50 100; do
  echo "Testing with concurrency: $concurrency"
  wrk -t 4 -c $concurrency -d 30s \
    -s variant-z/wrk_order_script.lua \
    http://localhost:30017/api/v1/orders/
done
```

---

## Expected Results

Based on the Python implementation benchmarking:

| Metric | Python | C# (Expected) | Java (Expected) |
|--------|---------|---------------|-----------------|
| Avg Latency | 14.12ms | ~10-15ms | ~8-12ms |
| P95 Latency | ~20ms | ~15-25ms | ~12-20ms |
| Throughput | ~1,800 req/s | ~2,000-3,000 req/s | ~2,500-4,000 req/s |
| Error Rate | 0% | 0% | 0% |

---

## Known Issues and Solutions

### Issue: Token System Not Initialized

**Symptom:** Orders fail with "TOKEN_NOT_AVAILABLE" or "REDIS_ERROR"

**Solution:**
```bash
docker exec flash-python-z python /app/allocate_all_campaign_tokens.py
```

### Issue: SKU Inventory Not Cached

**Symptom:** Orders fail with "SKU_NOT_CACHED"

**Solution:**
```bash
docker exec flash-python-z python -c "
import asyncio
from app.core.redis import redis_client

async def cache():
    await redis_client.cache_sku_inventory('2c2e23fa-f47b-4884-9b45-bf2a640f1ff3', 10000)

asyncio.run(cache())
"
```

### Issue: Campaign Sold Out

**Symptom:** Orders fail with "Flash sale sold out"

**Solution:**
```bash
docker exec flash-python-z python /app/reallocate_test_campaign_tokens.py
```

---

## Data Collection Template

Create a CSV file to track results:

```csv
Service,Concurrency,Duration,Throughput,Avg_Latency,P95_Latency,P99_Latency,Error_Rate,Total_Orders
Python,10,30s,,,,,,
Python,20,30s,,,,,,
Python,50,30s,,,,,,
Python,100,30s,,,,,,
CSharp,10,30s,,,,,,
CSharp,20,30s,,,,,,
CSharp,50,30s,,,,,,
CSharp,100,30s,,,,,,
Java,10,30s,,,,,,
Java,20,30s,,,,,,
Java,50,30s,,,,,,
Java,100,30s,,,,,,
```

---

## Next Steps

1. ✅ **Code fixes complete** - All services use "pending" status
2. ⏳ **Start services** - Run `docker-compose up -d`
3. ⏳ **Initialize tokens** - Run token allocation script
4. ⏳ **Verify health** - Check all three services
5. ⏳ **Run benchmarks** - Execute benchmark tests
6. ⏳ **Collect results** - Gather metrics
7. ⏳ **Generate report** - Create comparison analysis

---

## Files Modified

1. [`variant-z/csharp-service/Services/OrderService.cs`](variant-z/csharp-service/Services/OrderService.cs) - Fixed order status
2. [`variant-z/java-service/src/main/java/com/flashsale/service/OrderService.java`](variant-z/java-service/src/main/java/com/flashsale/service/OrderService.java) - Fixed order status

---

## Reference Implementation

The Python implementation serves as the reference for Variant Z architecture:

- **Token Manager:** [`variant-z/python-service/app/core/token_manager.py`](variant-z/python-service/app/core/token_manager.py)
- **Order Endpoint:** [`variant-z/python-service/app/api/endpoints/orders.py`](variant-z/python-service/app/api/endpoints/orders.py)
- **Redis Client:** [`variant-z/python-service/app/core/redis.py`](variant-z/python-service/app/core/redis.py)
- **Lua Script:** [`variant-z/acquire_order_token.lua`](variant-z/acquire_order_token.lua)

---

**Status:** ✅ Ready for Benchmarking  
**Last Updated:** 2026-01-14  
**Variant:** Z (Token Pre-Allocation)