# Debugging Guide - Variant Z Python Service

## Quick Reference

| Issue | Check | Command |
|-------|-------|---------|
| Service not starting | Container logs | `docker logs flash-python-z -f` |
| Connection refused | Service status | `docker-compose ps` |
| Redis errors | Redis connectivity | `docker exec flash-python-z python -c "..."` |
| Database errors | DB connectivity | `docker exec flash-mariadb-z mysql -u syracuse -p` |
| Token issues | Redis tokens | `docker exec flash-redis-z redis-cli ZCARD campaign:{id}:tokens` |

## Step-by-Step Debugging

### Phase 1: Service Startup Verification

#### 1.1 Check Container Status

```bash
# All services should be "Up"
docker-compose ps

# Expected output:
# NAME                STATUS              PORTS
# flash-mariadb-z     Up 2 minutes        0.0.0.0:3315->3306/tcp
# flash-redis-z       Up 2 minutes
# flash-python-z      Up 2 minutes        0.0.0.0:30017->8000/tcp
```

**If any service is not "Up":**
```bash
# Restart the service
docker-compose restart <service-name>

# Check logs
docker logs <service-name> --tail 50
```

#### 1.2 Check Python Service Health

```bash
# Test health endpoint
curl -i http://localhost:30017/health

# Expected: HTTP/1.1 200 OK
```

**If health check fails:**
```bash
# Check Python service logs
docker logs flash-python-z -f --tail 100

# Look for:
# - Connection errors (Redis/Database)
# - Import errors
# - Configuration errors
```

### Phase 2: Database Debugging

#### 2.1 Test Database Connection

```bash
# Connect to MariaDB
docker exec -it flash-mariadb-z mysql -u syracuse -p orange315
# Password: Orange_315_Forever!

# Test query
SHOW TABLES;
```

**Expected tables:**
- spus
- skus
- inventory
- flash_sale_campaigns
- orders
- order_line_items
- payments

**If tables are missing:**
```bash
# Run database initialization
docker exec flash-python-z python init_db.py
```

#### 2.2 Check Test Data

```bash
# Connect to database
docker exec -it flash-mariadb-z mysql -u syracuse -p orange315

# Check for test SPU
SELECT * FROM spus WHERE slug = 'flash-sale-test-product';

# Check for test SKU
SELECT * FROM skus WHERE sku_code = 'FS-TEST-BENCHMARK-001';

# Check inventory
SELECT * FROM inventory;

# Check flash sale campaign
SELECT * FROM flash_sale_campaigns WHERE status = 'active';
```

**If no test data exists:**
```bash
# Create test data
docker exec flash-python-z python setup_test_data.py
```

### Phase 3: Redis Debugging

#### 3.1 Test Redis Connection

```bash
# Connect to Redis CLI
docker exec -it flash-redis-z redis-cli

# Test connection
PING
# Expected: PONG

# Test Lua script availability
# (This is implicitly tested by token allocation)
```

**If Redis is not responding:**
```bash
# Check Redis logs
docker logs flash-redis-z -f

# Restart Redis
docker-compose restart redis
```

#### 3.2 Check Token Allocation

```bash
# Get campaign ID from test data output
CAMPAIGN_ID="<campaign-id-from-setup>"

# Check token count
docker exec flash-redis-z redis-cli ZCARD campaign:$CAMPAIGN_ID:tokens

# Expected: 10000 (or your campaign total_limit)
```

**If token count is 0:**
```bash
# Re-allocate tokens
docker exec flash-python-z python setup_test_data.py
```

#### 3.3 Check Campaign Metadata

```bash
CAMPAIGN_ID="<campaign-id-from-setup>"

# Get campaign metadata
docker exec flash-redis-z redis-cli GET campaign:$CAMPAIGN_ID:metadata

# Expected JSON:
# {"total_tokens": 10000, "remaining_tokens": 10000, "status": "active"}
```

#### 3.4 Check SKU Inventory Cache

```bash
SKU_ID="<sku-id-from-setup>"

# Get cached inventory
docker exec flash-redis-z redis-cli GET sku:$SKU_ID:inventory

# Expected: 10000 (or your inventory quantity)
```

**If cache is empty (nil):**
```bash
# The cache has 10-second TTL, it may have expired
# This is normal - it will be repopulated on next order
```

### Phase 4: Order Creation Testing

#### 4.1 Get Test Data IDs

```bash
# Run setup script to get IDs
docker exec flash-python-z python setup_test_data.py

# Copy the output:
# SKU ID:      <sku-id>
# Campaign ID: <campaign-id>
```

#### 4.2 Test Order Creation

```bash
# Replace <SKU_ID> with actual ID from setup
curl -X POST http://localhost:30017/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "customer_email": "test@example.com",
    "line_items": [{"sku_id": "<SKU_ID>", "quantity": 1}]
  }'
```

**Success Response (200):**
```json
{
  "order_id": "order-uuid",
  "status": "created",
  "total_amount": 99.99,
  "customer_email": "test@example.com"
}
```

**Error Response (400) - Sold Out:**
```json
{
  "error": "Flash sale sold out",
  "campaign_id": "campaign-uuid",
  "sold_out_at": "2026-01-13T05:00:00.000Z"
}
```

**Error Response (400) - Invalid SKU:**
```json
{
  "detail": "SKU not found"
}
```

#### 4.3 Verify Order in Database

```bash
# Connect to database
docker exec -it flash-mariadb-z mysql -u syracuse -p orange315

# Check latest order
SELECT * FROM orders ORDER BY created_at DESC LIMIT 1;

# Check order line items
SELECT * FROM order_line_items ORDER BY created_at DESC LIMIT 1;

# Check inventory decrement
SELECT * FROM inventory WHERE sku_id = '<SKU_ID>';

# Check campaign sold quantity
SELECT * FROM flash_sale_campaigns WHERE id = '<CAMPAIGN_ID>';
```

#### 4.4 Verify Token Consumption

```bash
CAMPAIGN_ID="<campaign-id>"

# Check remaining tokens
docker exec flash-redis-z redis-cli ZCARD campaign:$CAMPAIGN_ID:tokens

# Expected: 9999 (one token consumed)
```

### Phase 5: Load Testing

#### 5.1 Prepare for Load Test

```bash
# Ensure test data is fresh
docker exec flash-python-z python setup_test_data.py

# Verify tokens are allocated
CAMPAIGN_ID="<campaign-id>"
docker exec flash-redis-z redis-cli ZCARD campaign:$CAMPAIGN_ID:tokens

# Verify health
curl http://localhost:30017/health
```

#### 5.2 Run Load Test

```bash
# Using Python test script
python test_order.py http://localhost:30017 <SKU_ID>

# Using wrk (if available)
wrk -t4 -c100 -d30s \
  -s wrk_order_script.lua \
  http://localhost:30017/api/v1/orders
```

#### 5.3 Monitor During Load Test

```bash
# Terminal 1: Watch Python logs
docker logs flash-python-z -f

# Terminal 2: Monitor Redis tokens
watch -n 1 'docker exec flash-redis-z redis-cli ZCARD campaign:<id>:tokens'

# Terminal 3: Monitor database orders
watch -n 1 'docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e "SELECT COUNT(*) FROM orders;"'

# Terminal 4: Check system resources
docker stats
```

## Common Error Messages

### "Connection refused"

**Symptoms:**
- `curl: (7) Failed to connect to localhost port 30017`

**Solutions:**
1. Check service is running: `docker-compose ps`
2. Restart service: `docker-compose restart python-service`
3. Check logs: `docker logs flash-python-z`

### "Failed to connect to Redis"

**Symptoms:**
- Error in Python logs: `redis.exceptions.ConnectionError`
- Token acquisition fails

**Solutions:**
1. Check Redis is running: `docker-compose ps`
2. Test Redis connectivity: `docker exec flash-redis-z redis-cli PING`
3. Check network: `docker network inspect flashsale-z-net`
4. Restart Redis: `docker-compose restart redis`

### "SKU not found"

**Symptoms:**
- HTTP 400 response
- Error detail: "SKU not found"

**Solutions:**
1. Verify SKU ID is correct
2. Check database: `SELECT * FROM skus WHERE id = '<SKU_ID>'`
3. Check SKU is active: `SELECT * FROM skus WHERE sku_code = 'FS-TEST-BENCHMARK-001'`
4. Recreate test data: `docker exec flash-python-z python setup_test_data.py`

### "Flash sale sold out"

**Symptoms:**
- HTTP 400 response
- Error: "Flash sale sold out"

**Solutions:**
1. Check token count: `docker exec flash-redis-z redis-cli ZCARD campaign:<id>:tokens`
2. If 0, re-allocate tokens: `docker exec flash-python-z python setup_test_data.py`
3. Check campaign status: `SELECT * FROM flash_sale_campaigns WHERE id = '<id>'`

### "Insufficient stock"

**Symptoms:**
- HTTP 400 response
- Error: "Insufficient stock"

**Solutions:**
1. Check inventory: `SELECT * FROM inventory WHERE sku_id = '<SKU_ID>'`
2. Check Redis cache: `docker exec flash-redis-z redis-cli GET sku:<SKU_ID>:inventory`
3. Reset inventory: `UPDATE inventory SET quantity = 10000, reserved_quantity = 0 WHERE sku_id = '<SKU_ID>'`
4. Clear and repopulate cache: `docker exec flash-redis-z redis-cli DEL sku:<SKU_ID>:inventory`

### Database timeout

**Symptoms:**
- Slow order creation
- Timeout errors

**Solutions:**
1. Check database performance: `docker stats flash-mariadb-z`
2. Check connection pool settings in `app/core/database.py`
3. Reduce concurrent requests
4. Check MariaDB logs: `docker logs flash-mariadb-z`

## Performance Issues

### High Latency

**Symptoms:**
- Orders taking > 100ms
- Requests timing out

**Diagnosis:**
```bash
# Check database query time
docker exec flash-mariadb-z mysql -u syracuse -p orange315 -e "SHOW PROCESSLIST;"

# Check Redis latency
docker exec flash-redis-z redis-cli --latency

# Check Python service CPU
docker stats flash-python-z
```

**Solutions:**
1. Optimize database queries
2. Increase Redis connection pool size
3. Scale Python workers (already at 16)
4. Check system resources

### Low Throughput

**Symptoms:**
- < 1000 req/s during load test

**Diagnosis:**
```bash
# Check for bottlenecks
docker stats

# Check error rate in logs
docker logs flash-python-z 2>&1 | grep "ERROR"

# Check Redis hit rate
docker exec flash-redis-z redis-cli INFO stats | grep keyspace
```

**Solutions:**
1. Ensure Redis cache is warm
2. Check token allocation is complete
3. Verify database write performance
4. Check network bandwidth

## Log Analysis

### Structured Log Format

```json
{
  "asctime": "2026-01-13 05:00:00",
  "name": "app.api.endpoints.orders",
  "levelname": "INFO",
  "message": "[abc12345] REQUEST: POST /api/v1/orders",
  "request_id": "abc12345",
  "method": "POST",
  "path": "/api/v1/orders",
  "request_body": {...},
  "client_ip": "172.18.0.1"
}
```

### Extracting Metrics

```bash
# Count successful orders
docker logs flash-python-z 2>&1 | grep "Order created:" | wc -l

# Calculate average response time
docker logs flash-python-z 2>&1 | grep "RESPONSE:" | jq -r '.duration_sec' | awk '{sum+=$1; count++} END {print sum/count}'

# Find slow requests (> 100ms)
docker logs flash-python-z 2>&1 | grep "RESPONSE:" | jq 'select(.duration_sec > 0.1)'

# Count errors
docker logs flash-python-z 2>&1 | grep "ERROR" | wc -l
```

## Reset and Reinitialize

### Complete Reset

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Start fresh
docker-compose up -d mariadb redis python-service

# Wait for services (30 seconds)
sleep 30

# Initialize database
docker exec flash-python-z python init_db.py

# Setup test data
docker exec flash-python-z python setup_test_data.py
```

### Partial Reset (Keep Data)

```bash
# Restart services
docker-compose restart python-service

# Clear Redis
docker exec flash-redis-z redis-cli FLUSHALL

# Re-allocate tokens
docker exec flash-python-z python setup_test_data.py
```

## Advanced Debugging

### Enable SQL Query Logging

Edit `app/core/database.py`:

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Change to True
    # ... other settings
)
```

### Enable Redis Command Logging

```bash
# Monitor all Redis commands
docker exec flash-redis-z redis-cli MONITOR

# Press Ctrl+C to stop
```

### Debug Lua Script

```bash
# Test Lua script manually
docker exec flash-redis-z redis-cli --eval /app/acquire_order_token.lua , key1 key2 key3 , arg1 arg2 arg3

# Check Lua script loading
docker exec flash-python-z python -c "from app.core.redis import redis_client; import asyncio; asyncio.run(redis_client.connect())"
```

## Support Checklist

Before reporting issues, verify:

- [ ] Docker and Docker Compose are installed and running
- [ ] All containers are up: `docker-compose ps`
- [ ] Health check passes: `curl http://localhost:30017/health`
- [ ] Database tables exist: `SHOW TABLES;`
- [ ] Test data is created: `SELECT * FROM spus WHERE slug = 'flash-sale-test-product';`
- [ ] Tokens are allocated: `redis-cli ZCARD campaign:{id}:tokens`
- [ ] No errors in logs: `docker logs flash-python-z 2>&1 | grep -i error`
- [ ] Sufficient system resources: `docker stats`

## Contact

For additional support:
1. Review this guide
2. Check main README.md
3. Review IMPLEMENTATION_STATUS.md
4. Examine logs with `docker logs flash-python-z -f`