# Variant X - Redis Atomic Counters Implementation

This directory contains the **Variant X** implementation of the flash sale order processing system, which uses **Redis atomic counters** for lock-free inventory management during high-traffic flash sales.

## Overview

**Variant X** is an optimized architecture designed for extreme throughput flash sale scenarios. Unlike Variant Y (database-based transactions), this variant uses Redis DECRBY operations for atomic inventory reservations with zero database queries during the flash sale window.

## Key Differences from Variant Y

| Aspect | Variant Y (Main Directory) | Variant X (This Directory) |
|--------|---------------------------|----------------------------|
| **Architecture** | Database transactions | Redis atomic counters |
| **Inventory Method** | Row-level locks | DECRBY operations |
| **Flash Sale Queries** | 4-7 DB queries per order | 0 DB queries per order |
| **Throughput (Nginx)** | 2,136 req/s | 5,428 req/s (2.5× faster) |
| **Latency** | 65ms avg | 11ms avg (83% reduction) |
| **Persistence** | Synchronous | Async queue (Redis List) |

## Architecture Components

### Intelligent Routing
All three services (Python, Java, C#) implement intelligent routing:
- **Check SKU metadata in Redis**: If SKU is in active flash sale → Variant X path
- **Otherwise**: Falls back to Variant Y (database) path

### Redis Schema
```
# Campaign metadata
fs:{campaign_id}:meta → HASH {campaign_id, name, price, status, ...}

# Campaign inventory counter (atomic)
fs:{campaign_id}:limit → INTEGER (remaining inventory)

# SKU metadata (links SKU to flash sale)
sku:{sku_id}:meta → HASH {sku_id, flash_sale_id, flash_price, status, ...}

# SKU inventory counter (atomic)
inv:{sku_id} → INTEGER (remaining inventory)

# Order persistence queue
order_queue → LIST (async database writes)
```

### Atomic Reservation Flow
1. **Reserve from campaign limit** (Redis DECRBY)
   - If remaining < 0 → Rollback and fail
2. **Reserve from each SKU inventory** (Redis DECRBY)
   - If any SKU remaining < 0 → Rollback all and fail
3. **Queue order for async persistence** (Redis LPUSH)
4. **Return success immediately** (no DB wait)

## Running Variant X

### Prerequisites
- Podman 4.6.2+ (see `/versions/20251229-nginx-load-balanced-test/PODMAN_UPGRADE.md`)
- Static IPs configured (DNS doesn't work in Podman 4.6.2/WSL2)

### Start Services
```bash
cd /home/syracuse/orange-315-forever/variant-x
podman-compose -f docker-compose.yml up -d
```

### Container Names and Ports
All containers have "-x" suffix to avoid conflicts with Variant Y:
- **MariaDB**: `flash-mariadb-x` → localhost:3312
- **Redis**: `flash-redis-x` → (internal only)
- **Python**: `flash-python-x` → localhost:30011
- **Java**: `flash-java-x` → localhost:8016
- **C#**: `flash-csharp-x` → localhost:30012
- **Nginx**: `flash-nginx-x` → localhost:8445 (HTTPS)

### Load Flash Sale Data
```bash
# 1. Load campaigns to database
podman exec flash-python-x python setup_flash_sale_campaigns.py

# 2. Load flash sales to Redis (REQUIRED for Variant X)
podman exec flash-python-x python /tmp/load_flash_sales_to_redis.py
```

### Run Benchmark
```bash
# Flash sale specific test (ensures Variant X code path)
wrk -t8 -c50 -d10s --latency -s /tmp/wrk_flash_sale_order.lua \
  https://localhost:8445/api/v1/orders

# Expected: ~5,400 req/s with 11ms avg latency
```

## Test Results (December 29, 2025)

### Nginx Load Balanced (3 Services)
```
Requests/sec:     5,428 req/s
Latency (avg):    11.04ms
Latency (p50):    10.12ms
Latency (p99):    51.15ms
Total requests:   54,345 in 10s
Successful orders: 9,989 (depleted 10K inventory in ~2s)
Success rate:      18.4% (limited by 10K inventory)
```

**Comparison with Variant Y:**
- **2.5× faster throughput** (5,428 vs 2,136 req/s)
- **83% latency reduction** (11ms vs 65ms avg)
- **Zero overselling** (Redis atomic operations)

## Files Modified for Variant X

### Python Service
- `python-service/app/api/endpoints/orders.py` - Intelligent routing + Variant X implementation
- `python-service/app/core/redis_cache.py` - Redis operations for atomic counters
- `python-service/app/models/flash_sale.py` - Flash sale models
- `python-service/app/schemas/flash_sale.py` - Flash sale schemas

### Java Service
- `java-service/src/main/java/com/flashsale/api/service/OrderService.java` - Intelligent routing
- `java-service/src/main/java/com/flashsale/api/service/RedisCacheService.java` - Redis service
- `java-service/src/main/java/com/flashsale/api/entity/FlashSale.java` - Flash sale entity
- `java-service/src/main/java/com/flashsale/api/repository/FlashSaleRepository.java` - Repository
- `java-service/src/main/java/com/flashsale/api/config/RedisConfig.java` - Redis configuration

### C# Service
- `csharp-service/Services/OrderService.cs` - Intelligent routing + Variant X
- `csharp-service/Services/RedisCacheService.cs` - Redis cache service
- `csharp-service/Models/FlashSale.cs` - Flash sale models

### Database
- `migrations/001_add_flash_sale_campaigns.sql` - Flash sale schema

## Implementation Notes

### Why Intelligent Routing?
Instead of separate endpoints for flash sales, we use a single `/api/v1/orders` endpoint that automatically routes to the optimal implementation based on SKU metadata. This provides:
- **Seamless frontend integration** - No code changes needed
- **Automatic optimization** - Flash sales use Variant X, regular orders use Variant Y
- **Gradual rollout** - Can control which SKUs use Redis via metadata

### Async Persistence
Orders are queued to Redis Lists for async database writes. This decouples the critical path (inventory reservation) from slower database operations.

**Trade-off**: Orders may not appear in database immediately, but inventory is always correct.

### Zero Overselling Guarantee
Redis DECRBY is atomic at the operation level:
1. Multiple clients can DECRBY simultaneously
2. Each gets a unique remaining count
3. Negative results indicate overselling attempt
4. Application rolls back on negative results

## Stopping Services

```bash
cd /home/syracuse/orange-315-forever/variant-x
podman-compose -f docker-compose.yml down
```

## Documentation

See `/versions/20251229-nginx-load-balanced-test/` for:
- `SUMMARY.md` - Complete test methodology and results
- `PODMAN_UPGRADE.md` - Why Podman upgrade was needed
- `WORK_COMPLETED_20251229.md` - Development work summary

## Comparison with Variant Y

To compare both variants side-by-side:

```bash
# Terminal 1: Run Variant Y (main directory)
cd /home/syracuse/orange-315-forever
podman-compose up -d

# Terminal 2: Run Variant X (this directory)
cd /home/syracuse/orange-315-forever/variant-x
podman-compose up -d

# Both can run simultaneously with different ports
```

## Future Improvements

1. **Implement async database worker** - Currently orders are queued but not persisted
2. **Redis Cluster** - For high availability and horizontal scaling
3. **Circuit breaker** - Fallback to Variant Y if Redis fails
4. **Metrics and monitoring** - Track Redis operations, queue depth
5. **TTL management** - Auto-expire flash sale metadata after campaign ends
