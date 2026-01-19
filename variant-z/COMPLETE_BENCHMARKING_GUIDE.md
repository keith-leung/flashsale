# Complete Variant Z Benchmarking Guide

**Date:** 2026-01-14  
**Purpose:** Execute comprehensive benchmarking of Variant Z across Python, C#, and Java

---

## Pre-Flight Checklist

- [x] Code fixes applied (order status = "pending")
- [ ] Docker services running
- [ ] Health checks passing
- [ ] Tokens allocated in Redis
- [ ] SKU inventory cached
- [ ] Benchmark tests executed
- [ ] Results collected and analyzed

---

## Step 1: Start Docker Services

```bash
cd /home/syracuse/flashsale/variant-z
docker-compose up -d
```

**Wait 60 seconds** for services to initialize.

---

## Step 2: Verify Services Are Running

```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Expected output:
# flash-mariadb-z    Up
# flash-redis-z       Up
# flash-python-z      Up
# flash-java-z        Up
# flash-csharp-z      Up
# flash-nginx-z       Up
```

---

## Step 3: Health Checks

```bash
# Python (port 30017)
curl -s http://localhost:30017/health
# Expected: {"status":"ok"}

# C# (port 30018)
curl -s http://localhost:30018/health
# Expected: {"status":"ok"}

# Java (port 8019)
curl -s http://localhost:8019/health
# Expected: {"status":"ok"}
```

---

## Step 4: Initialize Test Data

### 4.1 Setup Database Tables

```bash
docker exec flash-python-z python /app/init_db.py
```

### 4.2 Create Test Campaigns and SKUs

```bash
docker exec flash-python-z python /app/setup_test_data.py 1 1 10000
```

### 4.3 Allocate Campaign Tokens (CRITICAL)

```bash
# Run token allocation script
docker exec flash-python-z python /app/allocate_all_campaign_tokens.py

# Verify tokens are allocated
docker exec flash-redis-z redis-cli ZCARD campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:tokens
# Expected: 9847 (or similar number)
```

### 4.4 Verify SKU Inventory Cache

```bash
docker exec flash-redis-z redis-cli GET sku:2c2e23fa-f47b-4884-9b45-bf2a640f1ff3:inventory
# Expected: 10000 (or similar number)
```

### 4.5 Verify Campaign Metadata

```bash
docker exec flash-redis-z redis-cli GET campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:metadata
# Expected: JSON with remaining_tokens
```

---

## Step 5: Test Single Order

### Python Service

```bash
curl -X POST http://localhost:30017/api/v1/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test User",
    "customer_email": "test@example.com",
    "line_items": [{
      "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
      "quantity": 1
    }]
  }'
# Expected: HTTP 201, status="pending"
```

### C# Service

```bash
curl -X POST http://localhost:30018/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "lineItems": [{
      "skuId": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
      "quantity": 1
    }]
  }'
# Expected: HTTP 201, status="pending"
```

### Java Service

```bash
curl -X POST http://localhost:8019/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "lineItems": [{
      "skuId": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
      "quantity": 1
    }]
  }'
# Expected: HTTP 201, status="pending"
```

---

## Step 6: Run Benchmarks

### Option A: Use Comprehensive Benchmark Script

```bash
cd /home/syracuse/flashsale/variant-z
bash benchmark_variant_z.sh 30
```

This will:
1. Check all services
2. Run health benchmarks (adaptive)
3. Run order benchmarks (adaptive)
4. Generate CSV results

### Option B: Manual Benchmarking

#### 6.1 Create Results Directory

```bash
mkdir -p /home/syracuse/flashsale/benchmark_results/variant_z
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CSV_FILE="/home/syracuse/flashsale/benchmark_results/variant_z/benchmark_${TIMESTAMP}.csv"
echo "service,concurrency,duration,req_per_sec,avg_latency_ms,p95_latency_ms,p99_latency_ms,errors_total,orders_created" > "$CSV_FILE"
```

#### 6.2 Python Benchmarks

```bash
# Concurrency 10
wrk -t 4 -c 10 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30017/api/v1/orders/

# Concurrency 20
wrk -t 4 -c 20 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30017/api/v1/orders/

# Concurrency 50
wrk -t 4 -c 50 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30017/api/v1/orders/

# Concurrency 100
wrk -t 4 -c 100 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30017/api/v1/orders/
```

#### 6.3 C# Benchmarks

```bash
# Concurrency 10
wrk -t 4 -c 10 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30018/api/v1/orders/

# Concurrency 20
wrk -t 4 -c 20 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30018/api/v1/orders/

# Concurrency 50
wrk -t 4 -c 50 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30018/api/v1/orders/

# Concurrency 100
wrk -t 4 -c 100 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:30018/api/v1/orders/
```

#### 6.4 Java Benchmarks

```bash
# Concurrency 10
wrk -t 4 -c 10 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:8019/api/v1/orders/

# Concurrency 20
wrk -t 4 -c 20 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:8019/api/v1/orders/

# Concurrency 50
wrk -t 4 -c 50 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:8019/api/v1/orders/

# Concurrency 100
wrk -t 4 -c 100 -d 30s -s /home/syracuse/flashsale/variant-z/wrk_order_script.lua http://localhost:8019/api/v1/orders/
```

---

## Step 7: Collect Results

### 7.1 Parse wrk Output

Each wrk run outputs:
- Requests/second
- Average latency
- P50/P95/P99 latency
- Total requests
- Errors

### 7.2 Record Results

Create a CSV file with format:

```csv
Service,Concurrency,Duration,Req_Per_Sec,Avg_Latency_ms,P95_Latency_ms,P99_Latency_ms,Total_Requests,Errors,Orders_Created
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

### 7.3 Verify Orders in Database

```bash
# Count total orders
docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "SELECT COUNT(*) as total_orders FROM orders;"

# Count orders by service (if using flash_sale_campaign_id)
docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "SELECT flash_sale_campaign_id, COUNT(*) as count FROM orders GROUP BY flash_sale_campaign_id;"

# Check order status distribution
docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "SELECT status, COUNT(*) as count FROM orders GROUP BY status;"
```

---

## Step 8: Analysis and Comparison

### 8.1 Compare Metrics

| Metric | Python | C# | Java | Best |
|--------|---------|-----|------|------|
| Avg Latency (c=50) | ? | ? | ? | ? |
| P95 Latency (c=50) | ? | ? | ? | ? |
| Throughput (c=50) | ? | ? | ? | ? |
| Error Rate | ? | ? | ? | ? |
| Max Concurrency | ? | ? | ? | ? |

### 8.2 Calculate Performance Improvements

```python
# Python baseline
python_throughput = 1800  # From previous benchmarks

# Calculate improvements
csharp_improvement = (csharp_throughput - python_throughput) / python_throughput * 100
java_improvement = (java_throughput - python_throughput) / python_throughput * 100
```

### 8.3 Analyze Latency Variance

Compare P99/P95 ratios:
- Lower ratio = more consistent performance
- Higher ratio = more outliers

### 8.4 Scalability Analysis

Plot throughput vs concurrency:
- Linear scaling = good
- Plateau = bottleneck
- Degradation = system limits

---

## Step 9: Create Comparison Report

Create file: `benchmark_results/VARIANT_Z_LANGUAGE_COMPARISON.md`

Template:

```markdown
# Variant Z Language Comparison Report

**Date:** [DATE]  
**Test Duration:** [DURATION]  
**Total Tests:** [COUNT]

## Executive Summary

[Summary of key findings]

## Test Configuration

### Hardware
- CPU: [CPU_COUNT] cores
- RAM: [RAM] GB
- Disk: [DISK_TYPE]

### Software
- MariaDB: [VERSION]
- Redis: [VERSION]
- Python: [VERSION]
- .NET: [VERSION]
- Java: [VERSION]

## Results

### Throughput Comparison

[Table with throughput at different concurrency levels]

### Latency Comparison

[Table with latency metrics]

### Error Rate Comparison

[Table with error rates]

## Analysis

### Performance Ranking

1. [Best Language]
2. [Second Best]
3. [Third Best]

### Key Findings

- [Finding 1]
- [Finding 2]
- [Finding 3]

### Recommendations

- [Recommendation 1]
- [Recommendation 2]
- [Recommendation 3]

## Conclusion

[Final verdict and production recommendations]
```

---

## Troubleshooting

### Issue: Orders failing with "TOKEN_NOT_AVAILABLE"

**Cause:** Campaign tokens not allocated in Redis

**Solution:**
```bash
docker exec flash-python-z python /app/allocate_all_campaign_tokens.py
```

### Issue: Orders failing with "SKU_NOT_CACHED"

**Cause:** SKU inventory not cached in Redis

**Solution:**
```bash
docker exec flash-python-z python -c "
import asyncio
from app.core.redis import redis_client

async def cache():
    await redis_client.connect()
    await redis_client.cache_sku_inventory('2c2e23fa-f47b-4884-9b45-bf2a640f1ff3', 10000)
    await redis_client.disconnect()

asyncio.run(cache())
"
```

### Issue: Orders failing with 404

**Cause:** Invalid SKU ID

**Solution:**
```bash
# Query valid SKUs
docker exec flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315 -e "SELECT id, sku_code FROM skus LIMIT 10;"

# Update wrk_order_script.lua with valid SKU ID
```

### Issue: High error rate (>5%)

**Cause:** System overload or configuration issue

**Solution:**
1. Check Docker resource limits
2. Reduce concurrency level
3. Check Redis memory usage
4. Check MariaDB connection pool

---

## Success Criteria

✅ All three services passing health checks  
✅ Tokens allocated in Redis  
✅ SKU inventory cached  
✅ Single order test passing for all services  
✅ Benchmarks completed at [10, 20, 50, 100] concurrency  
✅ Results collected and documented  
✅ Comparison report generated  
✅ Production recommendations provided  

---

## Quick Reference

### Service Ports

| Service | Port | Health | Orders |
|---------|-------|---------|---------|
| Python | 30017 | `/health` | `/api/v1/orders/` |
| C# | 30018 | `/health` | `/api/v1/orders` |
| Java | 8019 | `/health` | `/api/v1/orders` |

### Redis Commands

```bash
# Connect to Redis
docker exec -it flash-redis-z redis-cli

# Check remaining tokens
ZCARD campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:tokens

# Check SKU inventory
GET sku:2c2e23fa-f47b-4884-9b45-bf2a640f1ff3:inventory

# Check campaign metadata
GET campaign:e26bb7d0-c863-4cd6-b08c-44fcca0a8c28:metadata

# List all keys
KEYS "campaign:*"
KEYS "sku:*"
```

### Database Commands

```bash
# Connect to MariaDB
docker exec -it flash-mariadb-z mysql -usyracuse -pOrange_315_Forever! orange315

# Count orders
SELECT COUNT(*) FROM orders;

# Get recent orders
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;

# Check order status distribution
SELECT status, COUNT(*) FROM orders GROUP BY status;

# Verify inventory decrement
SELECT sku_id, quantity FROM inventory;
```

---

**Status:** ✅ Ready for Execution  
**Last Updated:** 2026-01-14  
**Variant:** Z (Token Pre-Allocation)