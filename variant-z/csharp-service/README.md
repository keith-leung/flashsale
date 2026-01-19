# Variant Z C# Service - Complete Implementation

**Status:** ✅ **IMPLEMENTED** - Token Pre-Allocation Architecture

---

## Overview

The C# service for Variant Z has been successfully implemented with the token pre-allocation architecture. It follows the same design as the Python and Java services, using Redis for fast token acquisition and synchronous database persistence for data integrity.

---

## Architecture

### Token Pre-Allocation

The C# service implements the Variant Z token pre-allocation strategy:

- **Token Storage:** Redis sorted sets with FIFO ordering via ZPOPMIN
- **Atomic Acquisition:** Lua script for atomic token + inventory operations
- **Synchronous Persistence:** Orders persisted to database before HTTP 201 response
- **SKU Inventory Cache:** Cached in Redis with NO TTL (inventory is source of truth)

### Key Components

1. **RedisService** - Redis client with connection pooling and Lua script caching
2. **TokenService** - Token pre-allocation and acquisition logic
3. **OrderService** - Order creation with synchronous database persistence
4. **HealthController** - Health check endpoint (GET/HEAD support)
5. **OrderController** - Order API endpoints

---

## Project Structure

```
variant-z/csharp-service/
├── FlashSale.csproj                  # Project file
├── Dockerfile                        # Container build configuration
├── appsettings.json                  # Application configuration
├── Program.cs                        # Application entry point
├── Models/                          # Entity models
│   ├── BaseEntity.cs
│   ├── Order.cs
│   ├── OrderLineItem.cs
│   ├── Payment.cs
│   ├── Sku.cs
│   ├── Inventory.cs
│   ├── Spu.cs
│   └── FlashSaleCampaign.cs
├── DTOs/                            # Data transfer objects
│   └── OrderDtos.cs
├── Data/                            # Database context
│   └── FlashSaleDbContext.cs
├── Services/                         # Business logic
│   ├── RedisService.cs
│   ├── TokenService.cs
│   └── OrderService.cs
├── Controllers/                      # API endpoints
│   ├── HealthController.cs
│   └── OrderController.cs
├── Resources/                        # Lua scripts
│   └── acquire_order_token.lua
└── benchmark_health_adaptive_sacred.sh  # SACRED benchmark script
```

---

## Configuration

### Database Connection

**File:** `appsettings.json`

```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=mariadb;Port=3306;Database=orange315;User=syracuse;Password=Orange_315_Forever!;"
  }
}
```

### Redis Configuration

**File:** `appsettings.json`

```json
{
  "Redis": {
    "Host": "redis",
    "Port": 6379,
    "Database": 0,
    "MaxConnections": 100
  }
}
```

---

## Implementation Details

### Token Pre-Allocation Flow

```
1. Campaign Activation:
   - Pre-allocate tokens to Redis sorted set (campaign:{id}:tokens)
   - Cache SKU inventory (sku:{sku_id}:inventory) - NO TTL
   - Set campaign metadata (campaign:{id}:metadata) - 60s TTL

2. Order Creation:
   - Check if SKU belongs to active campaign
   - Execute Lua script atomically:
     * ZPOPMIN to acquire token (FIFO)
     * Check and decrement SKU inventory
     * Update campaign metadata
   - Persist order to database synchronously
   - Return HTTP 201

3. Token Exhaustion:
   - When tokens reach zero, campaign is sold out
   - No database hit needed for sold-out check
```

### Lua Script

**File:** `Resources/acquire_order_token.lua`

```lua
-- KEYS[1]: campaign tokens key (campaign:{id}:tokens)
-- KEYS[2]: SKU inventory key (sku:{sku_id}:inventory)
-- KEYS[3]: Campaign metadata key (campaign:{id}:metadata)
-- ARGV[1]: Quantity to purchase
-- ARGV[2]: Campaign ID

local campaign_key = KEYS[1]
local sku_key = KEYS[2]
local metadata_key = KEYS[3]
local quantity = tonumber(ARGV[1])
local campaign_id = ARGV[2]

-- Step 1: Acquire token atomically using ZPOPMIN
local tokens = redis.call('ZPOPMIN', campaign_key, 1)
if not tokens or #tokens == 0 then
    return {err = "TOKEN_NOT_AVAILABLE"}
end

local token = tokens[1]

-- Step 2: Check and decrement SKU inventory
local current_stock = redis.call('GET', sku_key)
if not current_stock then
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "SKU_NOT_CACHED"}
end

current_stock = tonumber(current_stock)
if current_stock < quantity then
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "INSUFFICIENT_STOCK"}
end

redis.call('DECRBY', sku_key, quantity)

-- Update campaign metadata
local metadata = redis.call('GET', metadata_key)
if metadata then
    local decoded = cjson.decode(metadata)
    decoded.remaining_tokens = decoded.remaining_tokens - 1
    redis.call('SETEX', metadata_key, 60, cjson.encode(decoded))
end

return {ok = "ORDER_SUCCESS", remaining_stock = current_stock - quantity}
```

---

## API Endpoints

### Health Check

```
GET /health
HEAD /health

Response: 200 OK
```

### Create Order

```
POST /api/v1/orders
Content-Type: application/json

Request Body:
{
  "customerName": "Test User",
  "customerEmail": "test@example.com",
  "lineItems": [
    {
      "skuId": "uuid-of-sku",
      "quantity": 1
    }
  ]
}

Response (201 Created):
{
  "orderId": "uuid-of-order",
  "orderNumber": "ORD-timestamp-random",
  "status": "created",
  "totalAmount": 10.00,
  "customerEmail": "test@example.com"
}
```

### Get Order

```
GET /api/v1/orders/{id}

Response (200 OK):
{
  "orderId": "uuid-of-order",
  "orderNumber": "ORD-timestamp-random",
  "status": "created",
  "totalAmount": 10.00,
  "customerEmail": "test@example.com"
}
```

---

## Docker Integration

### Dockerfile

**File:** `Dockerfile`

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY FlashSale.csproj .
RUN dotnet restore "FlashSale.csproj"

COPY . .
RUN dotnet build "FlashSale.csproj" -c Release -o /app/build
RUN dotnet publish "FlashSale.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
COPY --from=build /app/publish .

ENV ASPNETCORE_URLS=http://+:80
ENV ASPNETCORE_ENVIRONMENT=Production

EXPOSE 80
ENTRYPOINT ["dotnet", "FlashSale.dll"]
```

### Docker Compose Configuration

The C# service is configured in [`variant-z/docker-compose.yml`](../docker-compose.yml):

```yaml
csharp-service:
  build:
    context: ./csharp-service
    dockerfile: Dockerfile
  container_name: flash-csharp-z
  restart: always
  cpus: "12.0"
  mem_limit: 4G
  ports:
    - "30018:80"
  environment:
    ConnectionStrings__DefaultConnection: "Server=mariadb;Port=3306;Database=orange315;User=syracuse;Password=Orange_315_Forever!;"
    ASPNETCORE_ENVIRONMENT: Development
    DB_HOST: mariadb
    REDIS_HOST: redis
    REDIS_PORT: 6379
  networks:
    - flashsale-z-net
  depends_on:
    - mariadb
    - redis
```

---

## Performance Targets

Based on Variant Z architecture:

| Metric | Target |
|--------|--------|
| Health Endpoint | 400,000 req/s |
| Orders Endpoint | 30,000 req/s |
| Latency (p99) | <50ms |
| vs Variant Y | 2.7x faster |

---

## Benchmarking

### SACRED Adaptive Health Benchmark

**File:** `benchmark_health_adaptive_sacred.sh`

This script follows the SACRED methodology for adaptive benchmarking:

- **Same algorithm** as Python and Java benchmarks
- **Same starting parameters** (t=4, c=10)
- **Same growth thresholds** (>5%, 2-5%, 0-2%)
- **Same stopping criteria** (plateau, 503, caps)
- **Same CSV schema** (27 fields)

**Usage:**

```bash
cd variant-z/csharp-service

# Set service URL (optional, defaults to http://localhost:30018)
export SERVICE_URL=http://localhost:30018

# Run benchmark
chmod +x benchmark_health_adaptive_sacred.sh
./benchmark_health_adaptive_sacred.sh
```

**Output:**

- CSV file: `csharp_health_adaptive_YYYYMMDD_HHMMSS.csv`
- Format: 27-field SACRED schema
- Fields: timestamp, variant, service, endpoint, test_type, threads, concurrency, duration_s, req_per_sec, latency_avg_ms, latency_stdev_ms, latency_p50_ms, latency_p75_ms, latency_p90_ms, latency_p95_ms, latency_p99_ms, latency_p99_9_ms, transfer_kb_sec, requests_total, errors_total, errors_rate, success_rate, connect_errors, read_errors, write_errors, timeout_errors, http_2xx, http_3xx, http_4xx, http_5xx, non_200_res

---

## Architecture Compliance

### ✅ Variant Z Compliance Checklist

- [x] Token pre-allocation in Redis sorted sets
- [x] Atomic token acquisition via Lua scripts (ZPOPMIN)
- [x] Synchronous database persistence (orders in DB before 201)
- [x] SKU inventory cache with NO TTL
- [x] Campaign metadata cache with 60s TTL
- [x] SACRED database schema compliance
- [x] SACRED API contract compliance (`/api/v1/orders`)
- [x] Health endpoint supports GET and HEAD
- [x] Environment isolation (10.92.0.0/24 network)
- [x] Syracuse credentials used everywhere

---

## Dependencies

**File:** `FlashSale.csproj`

```xml
<PackageReference Include="StackExchange.Redis" Version="2.6.122" />
<PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
<PackageReference Include="Pomelo.EntityFrameworkCore.MySql" Version="8.0.2" />
<PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
```

---

## Testing

### Health Check

```bash
# Check service health
curl http://localhost:30018/health

# Expected: 200 OK
```

### Order Creation Test

```bash
# Create an order
curl -X POST http://localhost:30018/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "lineItems": [{"skuId": "<SKU_ID>", "quantity": 1}]
  }'

# Expected: HTTP 201 with order_id
```

---

## Build and Run

### Local Development

```bash
# Build the project
dotnet build

# Run the application
dotnet run
```

### Docker Compose

```bash
cd variant-z
docker-compose up -d csharp-service

# View logs
docker-compose logs -f csharp-service
```

---

## References

- [Variant Z README](../README.md) - Main architecture documentation
- [Python Service README](../python-service/README.md) - Python implementation details
- [Java Service Implementation](../java-service/) - Java implementation details
- [SACRED VERIFICATION Documentation](../../docs/ADAPTIVE_TESTING.md) - Benchmarking methodology

---

**Last Updated:** 2026-01-13  
**Status:** ✅ Implemented - Ready for Benchmarking
**Variant:** Z
**Architecture:** Token Pre-Allocation with Atomic Redis Operations