# Variant Z Python Service - Simple Benchmark Tools

Simple benchmark tools for testing the Variant Z Python service performance.

## Quick Start

### 1. Start Services
```bash
cd variant-z
docker-compose up -d mariadb redis python-service
sleep 30
```

### 2. Setup Test Data
```bash
docker exec flash-python-z python init_db.py
docker exec flash-python-z python setup_test_data.py
```

### 3. Run Benchmark (Choose one)

#### Python Benchmark (Recommended)
```bash
# Get SKU ID from setup_test_data.py output
SKU_ID="<your-sku-id>"

python benchmark_simple.py --sku-id "$SKU_ID" --requests 10000 --concurrency 50
```

#### Shell Script Benchmark
```bash
./benchmark_simple.sh http://localhost:30017 30 100
```

## What These Benchmarks Test

1. **Token Pre-Allocation System**: Orders acquire tokens atomically via Redis Lua scripts
2. **Inventory Management**: SKU inventory cached in Redis with synchronous DB updates
3. **Database Persistence**: Orders persisted synchronously after token acquisition
4. **Concurrency Handling**: Multiple concurrent requests during flash sale

## Expected Performance

| Metric | Target | Variant Z Advantage |
|--------|--------|-------------------|
| Requests/sec | 3,000+ | 2.2x faster than Variant Y |
| Avg Latency | <50ms | Sub-5ms token acquisition |
| P95 Latency | <100ms | Efficient Redis + DB operations |

## Files Created

- [`benchmark_simple.py`](benchmark_simple.py) - Python async benchmark with detailed metrics
- [`benchmark_simple.sh`](benchmark_simple.sh) - Shell script using wrk for load testing
- [`BENCHMARK_GUIDE.md`](BENCHMARK_GUIDE.md) - Comprehensive benchmark guide

## Architecture Summary

Variant Z uses **Token Pre-Allocation** to eliminate database contention:

```
Request Flow:
1. POST /api/v1/orders
2. Check if SKU belongs to active campaign
3. Acquire token atomically via Redis Lua script (ZPOPMIN)
4. Decrement SKU inventory in Redis cache
5. Persist order to database (synchronous)
6. Return 201 Created
```

Key innovations:
- **Token Pre-Allocation**: Tokens pre-loaded into Redis sorted sets
- **Atomic Operations**: Lua scripts ensure consistency
- **Redis Caching**: SKU inventory cached without TTL
- **Synchronous Persistence**: Orders persisted before returning 201

## Troubleshooting

### Service Not Running
```bash
docker-compose ps
docker-compose up -d python-service
```

### No Test Data
```bash
docker exec flash-python-z python setup_test_data.py
```

### Tokens Exhausted
```bash
docker exec flash-python-z python setup_test_data.py
```

### Check Health
```bash
curl http://localhost:30017/health
```

## Verification Commands

```bash
# Check order count
docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 \
  -e 'SELECT COUNT(*) FROM orders;'

# Check remaining tokens
docker exec flash-redis-z redis-cli ZCARD "campaign:{campaign_id}:tokens"

# Check inventory
docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 \
  -e 'SELECT * FROM inventory WHERE sku_id = "<your-sku-id>";'
```

## Documentation

- [BENCHMARK_GUIDE.md](BENCHMARK_GUIDE.md) - Detailed benchmark guide
- [README.md](README.md) - Python service documentation
- [../README.md](../README.md) - Variant Z architecture overview

## Support

Check logs:
```bash
docker logs flash-python-z -f
```

For detailed troubleshooting, see [BENCHMARK_GUIDE.md](BENCHMARK_GUIDE.md).