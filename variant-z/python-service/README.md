# Variant Z Python Service - Token Pre-Allocation Architecture

## Overview

Variant Z implements a **Token Pre-Allocation** architecture for flash sale order processing. This approach eliminates database contention during high-traffic flash sales by pre-allocating purchase tokens in Redis and acquiring them atomically via Lua scripts.

### Key Innovations

- **Token Pre-Allocation**: Purchase tokens are pre-loaded into Redis sorted sets before campaign start
- **Atomic Redis Operations**: Lua scripts ensure atomic token acquisition and inventory updates
- **Synchronous Database Persistence**: Orders are persisted synchronously after token acquisition
- **Redis Inventory Caching**: SKU inventory is cached in Redis with 10-second TTL
- **No Async Complexity**: Simplified architecture without async background jobs

### Performance Target

- **Goal**: 3,000+ requests/second (2.2x faster than Variant Y)
- **Strategy**: Reduce database writes by 90% through token-based throttling

## Architecture

### Request Flow

```
1. Client POST /api/v1/orders
   ↓
2. Check if SKU belongs to active flash sale campaign
   ↓
3a. FLASH SALE PATH (Variant Z):
   - Check campaign sold-out status in Redis
   - Acquire token atomically via Lua script
   - Decrement Redis inventory cache
   - Create order in database (synchronous)
   
3b. REGULAR PATH (Variant Y):
   - Validate database inventory
   - Create order in database (synchronous)
   ↓
4. Return order confirmation
```

### Redis Data Structures

```
campaign:{campaign_id}:tokens      → Sorted Set (token_id, score)
campaign:{campaign_id}:metadata   → String (JSON, 60s TTL)
sku:{sku_id}:inventory            → String (quantity, 10s TTL)
```

### Lua Script (acquire_order_token.lua)

The Lua script executes atomically in Redis:

1. **ZREM** token from campaign tokens set
2. **GET** current SKU inventory from cache
3. **DECRBY** SKU inventory cache
4. **SETEX** update campaign metadata

All operations happen in a single atomic transaction.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Access to MariaDB and Redis services

### Start Services

```bash
# From variant-z directory
cd variant-z

# Start all services (MariaDB, Redis, Python)
docker-compose up -d mariadb redis python-service

# Wait for services to be ready (30 seconds)
sleep 30
```

### Initialize Database

```bash
# Initialize database tables
docker exec flash-python-z python init_db.py

# Setup test flash sale data
docker exec flash-python-z python setup_test_data.py
```

### Test Service

```bash
# Health check
curl http://localhost:30017/health

# Create an order (replace SKU_ID with actual ID from setup_test_data.py output)
curl -X POST http://localhost:30017/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "customer_email": "test@example.com",
    "line_items": [{"sku_id": "<SKU_ID>", "quantity": 1}]
  }'
```

### Run Test Script

```bash
# Using Python test script
python test_order.py http://localhost:30017 <SKU_ID>
```

## Project Structure

```
python-service/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   └── orders.py          # Order creation endpoint
│   │   ├── __init__.py
│   │   └── router.py              # API router
│   ├── core/
│   │   ├── database.py            # Database configuration
│   │   ├── logging.py             # Structured logging
│   │   ├── redis.py               # Redis client with pooling
│   │   └── token_manager.py       # Token pre-allocation logic
│   ├── models/
│   │   ├── flash_sale.py          # Flash sale campaign model
│   │   ├── inventory.py           # Inventory model
│   │   ├── order.py               # Order model
│   │   ├── order_line_item.py     # Order line item model
│   │   ├── payment.py             # Payment model
│   │   ├── sku.py                 # SKU model
│   │   └── spu.py                 # SPU model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── order.py               # Pydantic schemas
│   ├── __init__.py
│   └── main.py                   # FastAPI application
├── acquire_order_token.lua         # Atomic token acquisition script
├── Dockerfile                     # Container configuration
├── init_db.py                     # Database initialization script
├── setup_test_data.py             # Test data setup script
├── test_order.py                  # Order creation test
├── requirements.txt               # Python dependencies
└── START_SERVER.sh               # Startup script
```

## Configuration

### Environment Variables

```bash
DATABASE_URL=mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### Uvicorn Settings

```bash
--host 0.0.0.0
--port 8000
--workers 16              # 8 CPU cores * 2
--backlog 2048
--limit-concurrency 10000  # Max concurrent requests
```

## API Endpoints

### POST /api/v1/orders

Create a new order.

**Request:**
```json
{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "line_items": [
    {
      "sku_id": "550e8400-e29b-41d4-a716-446655440000",
      "quantity": 1
    }
  ],
  "currency": "USD"
}
```

**Success Response (200):**
```json
{
  "order_id": "order-uuid",
  "status": "created",
  "total_amount": 99.99,
  "customer_email": "john@example.com"
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

**Error Response (400) - Insufficient Stock:**
```json
{
  "error": "Insufficient stock",
  "sku_id": "sku-uuid",
  "available": 5
}
```

### GET /health

Health check endpoint.

**Response:**
```
200 OK
```

## Debugging

### View Logs

```bash
# View Python service logs
docker logs flash-python-z -f

# View logs with structured JSON
docker logs flash-python-z -f | jq
```

### Redis Debugging

```bash
# Connect to Redis CLI
docker exec -it flash-redis-z redis-cli

# Check campaign tokens
ZCARD campaign:{campaign_id}:tokens

# Check campaign metadata
GET campaign:{campaign_id}:metadata

# Check SKU inventory
GET sku:{sku_id}:inventory

# Monitor Redis commands
MONITOR
```

### Database Debugging

```bash
# Connect to MariaDB
docker exec -it flash-mariadb-z mysql -u syracuse -p orange315

# Check orders
SELECT COUNT(*) FROM orders;

# Check campaign sold quantity
SELECT sold_quantity FROM flash_sale_campaigns WHERE id = '{campaign_id}';

# Check inventory
SELECT * FROM inventory WHERE sku_id = '{sku_id}';
```

### Common Issues

#### 1. Connection Refused

**Problem**: `curl: (7) Failed to connect to localhost port 30017`

**Solution**: Ensure services are running:
```bash
docker-compose ps
docker-compose up -d python-service
```

#### 2. Redis Connection Error

**Problem**: `Failed to connect to Redis`

**Solution**: Check Redis is accessible:
```bash
docker exec flash-python-z python -c "import asyncio; from app.core.redis import redis_client; asyncio.run(redis_client.connect())"
```

#### 3. Token Not Available

**Problem**: `{"error": "Flash sale sold out"}`

**Solution**: Check token allocation:
```bash
docker exec flash-redis-z redis-cli ZCARD campaign:{campaign_id}:tokens
```

If 0, re-allocate tokens:
```bash
docker exec flash-python-z python setup_test_data.py
```

#### 4. Database Migration Issues

**Problem**: Tables not created

**Solution**: Run initialization:
```bash
docker exec flash-python-z python init_db.py
```

## Performance Testing

### Using wrk

```bash
# Benchmark order creation
wrk -t4 -c100 -d30s -s wrk_order_script.lua http://localhost:30017/api/v1/orders

# Expected results: 3,000+ req/s
```

### Using Custom Script

```bash
# Create test script
cat > test_load.sh << 'EOF'
#!/bin/bash
for i in {1..1000}; do
  curl -s -X POST http://localhost:30017/api/v1/orders \
    -H "Content-Type: application/json" \
    -d '{
      "customer_name": "Test",
      "customer_email": "test@example.com",
      "line_items": [{"sku_id": "<SKU_ID>", "quantity": 1}]
    }' &
done
wait
EOF

chmod +x test_load.sh
./test_load.sh
```

## Monitoring

### Structured Logging

Logs include:
- Request ID
- Method and path
- Request body
- Response status
- Duration
- Error details

Example:
```json
{
  "request_id": "abc12345",
  "method": "POST",
  "path": "/api/v1/orders",
  "status_code": 200,
  "duration_sec": 0.0234,
  "response_body": {
    "order_id": "order-uuid",
    "status": "created"
  }
}
```

### Key Metrics to Monitor

1. **Token Acquisition Rate**: Requests successfully acquiring tokens
2. **Token Depletion Rate**: Rate at which tokens are consumed
3. **Database Write Latency**: Time to persist orders
4. **Redis Operation Latency**: Time for token acquisition
5. **Error Rate**: Failed requests (sold out, insufficient stock)

## Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Clean up
docker system prune -f
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=mysql+aiomysql://syracuse:Orange_315_Forever!@localhost:3315/orange315
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_orders.py

# Run with coverage
pytest --cov=app --cov-report=html
```

## Troubleshooting Checklist

- [ ] All services running (`docker-compose ps`)
- [ ] Database initialized (`init_db.py`)
- [ ] Test data created (`setup_test_data.py`)
- [ ] Tokens allocated in Redis
- [ ] SKU inventory cached in Redis
- [ ] Health check passing (`/health`)
- [ ] Network connectivity (ping containers)
- [ ] No resource limits hit (CPU, memory)

## Support

For issues or questions:
1. Check logs: `docker logs flash-python-z -f`
2. Review this README's Debugging section
3. Check IMPLEMENTATION_STATUS.md for known issues
4. Verify Docker and system requirements

## License

Proprietary - Syracuse Orange 315 Flash Sale Platform