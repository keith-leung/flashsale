# Variant Z Python Service - Simple Benchmark Guide

This guide explains how to benchmark the Variant Z Python service using simple scripts.

## Overview

Variant Z implements a **Token Pre-Allocation** architecture that targets **3,000+ requests/second** for order creation during flash sales.

### Key Architecture Features

- **Token Pre-Allocation**: Purchase tokens pre-loaded into Redis sorted sets
- **Atomic Redis Operations**: Lua scripts ensure atomic token acquisition
- **Synchronous Database Persistence**: Orders persisted synchronously after token acquisition
- **Redis Inventory Caching**: SKU inventory cached in Redis (no TTL)

## Prerequisites

1. **Docker and Docker Compose** installed
2. **Services running**: MariaDB, Redis, Python service
3. **Test data setup**: Flash sale campaign with tokens allocated

## Quick Start

### 1. Start Services

```bash
cd variant-z
docker-compose up -d mariadb redis python-service

# Wait for services to be ready (30 seconds)
sleep 30
```

### 2. Initialize Database

```bash
# Initialize database tables
docker exec flash-python-z python init_db.py

# Setup test flash sale data
docker exec flash-python-z python setup_test_data.py
```

### 3. Verify Service Health

```bash
curl http://localhost:30017/health
# Expected: "200 OK"
```

### 4. Run Benchmark

Choose one of the following methods:

#### Option A: Python Benchmark (Recommended)

```bash
# Get SKU ID from setup_test_data.py output
SKU_ID="<your-sku-id>"

# Run benchmark
python benchmark_simple.py --sku-id "$SKU_ID" --requests 10000 --concurrency 50
```

#### Option B: Shell Script with wrk

```bash
# Make script executable
chmod +x benchmark_simple.sh

# Run benchmark
./benchmark_simple.sh http://localhost:30017 30 100
```

## Benchmark Scripts

### benchmark_simple.py

Python-based benchmark with detailed metrics.

**Features:**
- Concurrent async requests using httpx
- Detailed latency statistics (P50, P95, P99)
- Error tracking and categorization
- JSON results export
- Real-time progress updates

**Usage:**
```bash
python benchmark_simple.py [OPTIONS]

Options:
  --url TEXT              Base URL of the service (default: http://localhost:30017)
  --sku-id TEXT           SKU ID to use for orders (required)
  --requests INTEGER      Total number of requests (default: 10000)
  --concurrency INTEGER   Number of concurrent workers (default: 50)
```

**Example:**
```bash
python benchmark_simple.py \
  --url http://localhost:30017 \
  --sku-id "550e8400-e29b-41d4-a716-446655440000" \
  --requests 10000 \
  --concurrency 50
```

### benchmark_simple.sh

Shell script using wrk for HTTP load testing.

**Features:**
- Automatic health check
- Automatic SKU ID detection
- wrk-based load testing
- Response breakdown (success vs errors)

**Usage:**
```bash
./benchmark_simple.sh [BASE_URL] [DURATION] [CONCURRENCY]

Arguments:
  BASE_URL      Service base URL (default: http://localhost:30017)
  DURATION      Test duration in seconds (default: 30)
  CONCURRENCY   Number of concurrent connections (default: 100)
```

**Example:**
```bash
./benchmark_simple.sh http://localhost:30017 30 100
```

## Expected Results

### Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Requests/sec | 3,000+ | 2.2x faster than Variant Y |
| Avg Latency | <50ms | Token acquisition is sub-5ms |
| P95 Latency | <100ms | Database persistence adds latency |
| Error Rate | 0% | Until tokens exhausted |

### Sample Output

```
======================================================================
BENCHMARK RESULTS
======================================================================
Total Requests:      10000
Successful:          10000
Failed:              0
Duration:            3.33s
Requests/sec:        3003.00

Latency:
  Average:           33.2ms
  P50 (median):      31.5ms
  P95:               45.8ms
  P99:               52.1ms

======================================================================
Performance Analysis
======================================================================
✓ Target achieved: 3003.00 req/s (target: 3000 req/s)
```

## Verification

### Check Order Count

```bash
docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 \
  -e 'SELECT COUNT(*) as total_orders FROM orders;'
```

### Check Remaining Tokens

```bash
# Get campaign ID from setup_test_data.py output
CAMPAIGN_ID="<your-campaign-id>"

docker exec flash-redis-z redis-cli ZCARD "campaign:{campaign_id}:tokens"
```

### Check Inventory

```bash
docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 \
  -e 'SELECT sku_id, quantity, reserved_quantity FROM inventory WHERE sku_id = "<your-sku-id>";'
```

## Troubleshooting

### Service Not Running

**Problem:** `curl: (7) Failed to connect to localhost port 30017`

**Solution:**
```bash
docker-compose ps
docker-compose up -d python-service
```

### No Test Data

**Problem:** `Test SKU not found`

**Solution:**
```bash
docker exec flash-python-z python setup_test_data.py
```

### Tokens Exhausted

**Problem:** All requests return "Flash sale sold out"

**Solution:**
```bash
# Re-allocate tokens
docker exec flash-python-z python setup_test_data.py
```

### Connection Refused

**Problem:** `Connection refused` errors during benchmark

**Solution:**
```bash
# Check service health
curl http://localhost:30017/health

# Check logs
docker logs flash-python-z --tail 50
```

### Low Performance

**Problem:** Requests/sec significantly below 3,000

**Possible Causes:**
1. **Database connection pool exhausted**: Increase pool size in [`database.py`](app/core/database.py)
2. **Redis connection issues**: Check Redis logs
3. **CPU limits**: Check Docker resource allocation
4. **Network latency**: Ensure services are on same Docker network

**Debug Steps:**
```bash
# Check CPU usage
docker stats flash-python-z

# Check database connections
docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 \
  -e 'SHOW PROCESSLIST;' | wc -l

# Check Redis connections
docker exec flash-redis-z redis-cli CLIENT LIST | wc -l
```

## Advanced Benchmarking

### Test Different Concurrency Levels

```bash
# Low concurrency (10 workers)
python benchmark_simple.py --sku-id "$SKU_ID" --requests 1000 --concurrency 10

# Medium concurrency (50 workers)
python benchmark_simple.py --sku-id "$SKU_ID" --requests 5000 --concurrency 50

# High concurrency (100 workers)
python benchmark_simple.py --sku-id "$SKU_ID" --requests 10000 --concurrency 100
```

### Test Token Exhaustion

```bash
# Send more requests than available tokens
python benchmark_simple.py --sku-id "$SKU_ID" --requests 15000 --concurrency 100
```

Expected behavior:
- First 10,000 requests succeed (campaign limit)
- Remaining requests fail with "Flash sale sold out"

### Stress Test Database

```bash
# High concurrency to test database connection pool
python benchmark_simple.py --sku-id "$SKU_ID" --requests 50000 --concurrency 200
```

## Performance Optimization Tips

### 1. Database Connection Pool

Edit [`app/core/database.py`](app/core/database.py):
```python
engine = create_async_engine(
    database_url,
    pool_size=20,          # Increase from default
    max_overflow=40,       # Increase from default
    pool_pre_ping=True,
    echo=False
)
```

### 2. Redis Connection Pool

Edit [`app/core/redis.py`](app/core/redis.py):
```python
self.pool = redis.ConnectionPool(
    host=redis_host,
    port=redis_port,
    db=redis_db,
    max_connections=50,    # Increase pool size
    decode_responses=True
)
```

### 3. Uvicorn Workers

Edit [`START_SERVER.sh`](START_SERVER.sh):
```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 16 \          # Increase workers
  --backlog 2048 \
  --limit-concurrency 10000
```

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Clean up benchmark results
rm -f benchmark_results_variant_z_*.json
```

## Additional Resources

- [Variant Z README](../README.md) - Architecture overview
- [Python Service README](README.md) - Service documentation
- [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md) - Debugging tips
- [TEST_RESULTS.md](TEST_RESULTS.md) - Test results

## Support

For issues or questions:
1. Check service logs: `docker logs flash-python-z -f`
2. Review this guide's Troubleshooting section
3. Check [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
4. Verify Docker and system requirements