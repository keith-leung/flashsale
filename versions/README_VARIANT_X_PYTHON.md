# Python Service - Variant X (Redis-Only Architecture)

## Overview

**Variant X** is a Redis-optimized implementation of the Flash Sale Python service, designed to minimize database round-trips during order creation by aggressively caching SKU and inventory data in Redis.

## Architecture Differences from Variant Y (Baseline)

| Aspect | Variant Y (Baseline) | Variant X (Redis-Only) |
|--------|---------------------|----------------------|
| **SKU Reads** | Direct database query per SKU (N+1 problem) | Redis cache-aside pattern with batch prefetch |
| **Database Queries** | ~4-7 per order (1 order + 3 SKU selects + inventory updates) | ~1-2 per order (1 order + batch SKU load on cache miss) |
| **Redis Usage** | Not used | Aggressive caching with smart TTLs |
| **Cache Strategy** | No caching | Cache-aside with batch pipeline operations |
| **Redis Resources** | 2 CPUs, 2GB RAM | 6 CPUs, 6GB RAM |

## Key Optimizations

### 1. Batch Redis Prefetch (Pipeline)

Instead of querying the database once per SKU:
```python
# Variant Y (Baseline) - N database queries
for item in order_items:
    sku = await db.execute(select(SKU).filter(SKU.id == item.sku_id))
```

Variant X fetches all SKUs from Redis in a single pipeline operation:
```python
# Variant X - Single Redis pipeline
sku_ids = [item.sku_id for item in order_items]
cached_skus = await cache.get_multi_sku(sku_ids)  # Single pipeline call
```

### 2. Cache-Aside Pattern with Smart TTLs

- **SKU Data**: 10 minute TTL (changes infrequently)
- **Inventory Data**: 1 minute TTL (changes frequently during flash sales)
- **Cache Invalidation**: Automatic on inventory updates

### 3. Reduced Database Load

**Variant Y Performance Profile:**
- 3 SKUs in order = 3 separate `SELECT` queries to database
- Each query involves network round-trip + query execution
- Total: ~6-9 database operations per order

**Variant X Performance Profile:**
- 3 SKUs in order = 1 Redis pipeline operation (cache hit)
- On cache miss: 1 batched `SELECT WHERE id IN (...)` query
- Total: ~2-3 database operations per order (67% reduction)

### 4. Performance Metrics Logging

Variant X tracks and logs cache performance:
```
Cache performance: 450 hits, 50 misses (90.0% hit rate)
```

## Files Modified/Added

### New Files

1. **`app/core/redis_cache.py`**
   - Redis cache manager class
   - Cache-aside pattern implementation
   - Batch prefetch with pipeline
   - TTL management

2. **`app/api/endpoints/orders_variant_x.py`**
   - Redis-optimized order creation logic
   - Batch SKU prefetch
   - Cache hit rate tracking
   - Reduced database queries

3. **`README_VARIANT_X.md`** (this file)
   - Architecture documentation

### Modified Files

1. **`app/main.py`**
   - Added Redis connection in lifespan
   - Initialize cache on startup
   - Close cache on shutdown

2. **`app/api/endpoints/orders.py`**
   - `create_order` now delegates to `create_order_variant_x`

3. **`requirements.txt`**
   - Enabled `redis>=5.1.1`

4. **`Dockerfile`**
   - No changes needed (reuses Variant Y Dockerfile)

## Configuration

### Environment Variables

```bash
# Database (same as Variant Y)
DATABASE_URL=mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315

# Redis (required for Variant X)
REDIS_URL=redis://redis:6379/0
```

### Docker Compose

```yaml
python-service-variant-x:
  build:
    context: ./python-service-variant-x
  ports:
    - "8100:8000"  # Port 8100 (non-overlapping with Variant Y)
  environment:
    DATABASE_URL: mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315
    REDIS_URL: redis://redis:6379/0
  depends_on:
    - mariadb
    - redis
```

## Running Variant X

### Using Docker Compose

```bash
# Start Variant X services
podman-compose -f docker-compose-variant-x.yml up -d

# Check service health
curl http://localhost:8100/health  # Python Variant X

# Test order creation
cd python-service-variant-x
wrk -t12 -c100 -d30s -s wrk_order_script.lua http://localhost:8100/api/v1/orders
```

### Standalone (without Docker)

```bash
cd python-service-variant-x

# Install dependencies
pip install -r requirements.txt

# Start Redis (if not using Docker)
redis-server --port 6379

# Start MariaDB (existing WSL instance)
# (Already running on 127.0.0.1:3306)

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8100
```

## Expected Performance Improvements

Based on the architectural changes, we expect:

1. **Reduced Database Load**: 50-70% fewer database queries
2. **Lower Latency**: 20-40% reduction in order creation latency (on cache hit)
3. **Higher Throughput**: 30-50% increase in orders/sec under high load
4. **Better Scalability**: Database becomes less of a bottleneck

**Benchmark Comparison (Target):**
```
Variant Y (Baseline): 1,484 orders/sec @ 96.9% success
Variant X (Redis):    2,000+ orders/sec @ 97%+ success (estimated)
```

## Cache Performance Monitoring

Variant X logs cache metrics for every order:

```json
{
  "order_number": "ORD-123456",
  "variant": "X",
  "cache_hits": 3,
  "cache_misses": 0,
  "hit_rate": "100.0%"
}
```

## Trade-offs

### Advantages
- ✅ Significantly reduced database load
- ✅ Lower latency on cache hits
- ✅ Higher throughput potential
- ✅ Better scalability for read-heavy workloads

### Disadvantages
- ⚠️ Cache warming required (first requests are slower)
- ⚠️ Eventual consistency (1-10 minute staleness depending on TTL)
- ⚠️ Additional Redis infrastructure required
- ⚠️ More complex codebase

## Future Enhancements

1. **Cache Warming**: Pre-populate Redis on startup with hot SKUs
2. **Write-Through Cache**: Update cache immediately on SKU/inventory changes
3. **Redis Cluster**: Horizontal scaling for extreme loads
4. **Cache Monitoring**: Dashboard for hit rates and performance metrics

## Comparison Matrix

| Metric | Variant Y | Variant X | Improvement |
|--------|-----------|-----------|-------------|
| Database queries/order | 4-7 | 1-2 | 67% reduction |
| Redis queries/order | 0 | 1 (pipeline) | N/A |
| Cache hit rate | N/A | 80-95% (expected) | N/A |
| Orders/sec | 1,484 | TBD (benchmark) | Target: +30-50% |
| Success rate | 96.9% | TBD (benchmark) | Target: >97% |

## Testing Checklist

- [ ] Service starts successfully
- [ ] Redis connection established
- [ ] Order creation works (cache miss)
- [ ] Order creation works (cache hit)
- [ ] Cache metrics logged
- [ ] Benchmark with wrk
- [ ] Compare with Variant Y baseline

## Notes

- **Port Allocation**: Uses port 8100 to avoid conflict with Variant Y (8000)
- **Database Sharing**: Uses same MariaDB database as Variant Y
- **Non-Overlapping**: Can run simultaneously with Variant Y for A/B testing
