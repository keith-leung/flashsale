# Flash Sale Microservices Platform

A complete flash sale e-commerce platform with identical functionality implemented in **Python, C#, and Java**. Designed for performance testing and architectural comparison.

## Latest Benchmark Results (Static IP Network - Dec 27, 2025)

**Environment:** Podman containers with static IP allocation (10.88.0.0/16 subnet)
- **CPU:** Intel Core Ultra 9 275HX - P-cores (0-7) for middleware, E-cores (8-23) for apps
- **Memory:** 16GB MariaDB, 2GB Redis, 4GB per application
- **Test Data:** 500 SPUs, 2,500 SKUs, 25M total stock
- **Load Test:** wrk -t12 -c100 -d30s

### Variant Y Results (Baseline Architecture)

| Service | Throughput | Latency (avg) | Total Requests | vs Python |
|---------|-----------|---------------|----------------|-----------|
| **C# (ASP.NET Core)** | **4,663 req/s** | **25.15ms** | 152,422 | **3.6× faster** |
| **Java (Spring Boot)** | **3,592 req/s** | **26.63ms** | 116,110 | **2.8× faster** |
| **Python (FastAPI)** | 1,297 req/s | 113.97ms | 39,840 | baseline |

**Key Findings:**
- C# demonstrates best performance for high-throughput flash sales
- All services are database I/O-bound (4-7 queries per order)
- Static IP networking resolves Podman DNS reliability issues
- 100% success rates across all three implementations

**Production Capacity (10K orders/sec target):**
- C# requires 2-3 instances
- Java requires 3-4 instances
- Python requires 8-10 instances

## Quick Start - Dockerized Setup

```bash
# Start Variant Y (baseline) with static IP network
podman-compose -f docker-compose-variant-y.yml up -d

# Verify static IPs
podman inspect flash-mariadb flash-python flash-java flash-csharp | grep IPAddress

# Check service health
curl http://localhost:8000/health  # Python
curl http://localhost:8081/health  # Java
curl http://localhost:8082/health  # C#

# Generate test data
podman exec flash-python python /app/setup_test_data.py 500 5 10000

# Copy SKU IDs for benchmarks
podman cp flash-python:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt

# Run benchmarks
wrk -t12 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8000/api/v1/orders
wrk -t12 -c100 -d30s -s java-service/wrk_order_script.lua http://localhost:8081/api/v1/orders
wrk -t12 -c100 -d30s -s csharp-service/wrk_order_script.lua http://localhost:8082/api/v1/orders
```

### Network Architecture

**Static IP Allocation (10.88.0.0/16 subnet):**
- MariaDB: 10.88.0.2:3306
- Redis: 10.88.0.3:6379
- Nginx: 10.88.0.4:443
- Python: 10.88.0.5:8000 (host: 8000)
- Java: 10.88.0.6:8080 (host: 8081)
- C#: 10.88.0.7:80 (host: 8082)

**Why Static IPs:** Podman 3.4.4 has unreliable DNS resolution in container networking. Static IP allocation ensures consistent connectivity.

### CPU Allocation Strategy

**Hardware:** Intel Core Ultra 9 275HX (8 P-cores + 16 E-cores)

**P-Cores (0-7) - Middleware:**
- MariaDB: 8 cores, 16GB RAM
- Redis: 2 cores, 2GB RAM
- Nginx: 1 core, 512MB RAM

**E-Cores (8-23) - Applications:**
- Python: 4 cores, 4GB RAM
- Java: 4 cores, 4GB RAM
- C#: 4 cores, 4GB RAM

**Rationale:** Middleware (database, cache, load balancer) requires P-cores for maximum I/O throughput. Applications are I/O-bound and run efficiently on E-cores.

## Overview

Three independent microservices implementing flash sale functionality:

1. **Python Service** - FastAPI + SQLAlchemy + MariaDB + Redis
2. **C# Service** - ASP.NET Core + EF Core + MariaDB + Redis
3. **Java Service** - Spring Boot + JPA + MariaDB + Redis

## Core Features

### Product Management
- **SPU (Standard Product Unit)** - Product catalog with slug-based identification
- **SKU (Stock Keeping Unit)** - Product variants with pricing and inventory

### Flash Sale Events
- Time-based sales with start/end times
- Total sale limits and per-customer quantity restrictions
- Real-time status updates (Scheduled → Active → Ended)
- Automatic inventory management

### Order Processing
- Full ACID transaction support
- Inventory reservation and fulfillment
- Multi-item orders with line items
- Real-time stock tracking

## Architecture Principles

- **Domain-Driven Design** - Clear separation of concerns
- **API-First** - RESTful APIs with OpenAPI/Swagger documentation
- **Database-First** - Manual SQL schema migrations (no code-first)
- **Scalability** - Redis caching, async operations, background tasks
- **Data Integrity** - Database constraints, optimistic concurrency, transactions

## Service Comparison

| Feature | Python (FastAPI) | C# (ASP.NET Core) | Java (Spring Boot) |
|---------|------------------|-------------------|-------------------|
| **Language** | Python 3.11+ | C# .NET 8 | Java 21+ |
| **Web Framework** | FastAPI | ASP.NET Core | Spring Boot 3.2 |
| **ORM** | SQLAlchemy | EF Core | Spring Data JPA |
| **Database** | MariaDB (InnoDB) | MariaDB (InnoDB) | MariaDB (InnoDB) |
| **Caching** | Redis | Redis | Redis |
| **Documentation** | OpenAPI/Swagger | Swagger | SpringDoc |

## Important Conventions

### 1. ID Generation (Snowflake-style)
All IDs are **time-based, incrementing UUID-style identifiers**. They are NOT random UUIDs - IDs increase over time.

### 2. Database Schema Migrations
**Database-first approach** - All schema changes via manual SQL scripts. Code-first migrations are forbidden.

### 3. Python/FastAPI Patterns
- **UUIDs in Queries**: Convert UUID objects to strings (`str(uuid_object)`) before database queries
- **Eager Loading**: Use `selectinload()` for relationships in async contexts to prevent lazy loading errors

### 4. Proactive Bug Resolution
When fixing a bug, scan the entire codebase for similar patterns and apply the fix everywhere.

## Database Schema

**Core Models:**
- **SPU**: Product catalog entries
- **SKU**: Product variants with pricing
- **Inventory**: Stock levels and reservations
- **Flash Sale Events**: Time-limited promotions
- **Orders**: Customer purchases
- **Order Line Items**: Items within orders
- **Payments**: Payment transactions

**All IDs**: UUID format (CHAR(36)) for distributed generation

## API Endpoints

All services expose identical REST APIs:

### SPU Endpoints
- `GET /api/v1/spus` - List SPUs
- `POST /api/v1/spus` - Create SPU
- `GET /api/v1/spus/{id}` - Get SPU
- `PUT /api/v1/spus/{id}` - Update SPU
- `DELETE /api/v1/spus/{id}` - Delete SPU

### SKU Endpoints
- `GET /api/v1/skus` - List SKUs
- `POST /api/v1/skus` - Create SKU
- `GET /api/v1/skus/{id}` - Get SKU
- `PUT /api/v1/skus/{id}` - Update SKU
- `DELETE /api/v1/skus/{id}` - Delete SKU

### Flash Sale Endpoints
- `GET /api/v1/flash-sales` - List flash sales
- `POST /api/v1/flash-sales` - Create flash sale
- `GET /api/v1/flash-sales/{id}` - Get flash sale
- `PUT /api/v1/flash-sales/{id}` - Update flash sale
- `POST /api/v1/flash-sales/{id}/purchase` - Purchase from sale
- `DELETE /api/v1/flash-sales/{id}` - Delete flash sale

### Order Endpoints
- `GET /api/v1/orders` - List orders
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders/{id}` - Get order

### Inventory Endpoints
- `GET /api/v1/inventory/{sku_id}` - Get inventory
- `PUT /api/v1/inventory/{sku_id}` - Update inventory
- `POST /api/v1/inventory/{sku_id}/adjust` - Adjust quantity
- `POST /api/v1/inventory/{sku_id}/reserve` - Reserve stock
- `POST /api/v1/inventory/{sku_id}/release` - Release reserved stock

## Business Logic

### Flash Sale State Management
- **Scheduled** → **Active** (when current time >= start_time)
- **Active** → **Ended** (when current time >= end_time OR sold >= limit)
- **Any State** → **Cancelled** (manual)

### Inventory Management
- **Available Quantity** = Total - Reserved
- **Reservation System** prevents overselling
- **Fulfillment** reduces both reserved and total quantities

### Concurrency Handling
- Database-level constraints (unique slugs/SKU codes)
- Optimistic locking for inventory updates
- Transaction boundaries for multi-step operations

## Technology Choices

### Why MariaDB with InnoDB?
- **Row-level locking**: Prevents overselling with minimal contention
- **MVCC**: Multiple reads during writes
- **ACID compliance**: Data integrity during flash sales
- **Battle-tested**: Proven for e-commerce workloads

### Why Redis?
- High-performance caching for read-heavy workloads
- Session storage
- Real-time data access

### Why These Frameworks?
- **Python/FastAPI**: Rapid development, async support, strong typing
- **C#/ASP.NET Core**: Enterprise performance, excellent tooling
- **Java/Spring Boot**: Battle-tested ecosystem, comprehensive features

## Testing Flash Sales

```bash
# 1. Create flash sale
curl -X POST http://localhost:8000/api/v1/flash-sales \
  -H "Content-Type: application/json" \
  -d '{
    "sku_id": "...",
    "start_time": "2025-12-27T12:00:00Z",
    "end_time": "2025-12-27T13:00:00Z",
    "total_sale_limit": 100,
    "max_quantity_per_customer": 2
  }'

# 2. Purchase from flash sale
curl -X POST http://localhost:8000/api/v1/flash-sales/{id}/purchase \
  -H "Content-Type: application/json" \
  -d '{"quantity": 1}'

# 3. Test overselling protection (should fail)
curl -X POST http://localhost:8000/api/v1/flash-sales/{id}/purchase \
  -H "Content-Type: application/json" \
  -d '{"quantity": 200}'
```

## Database Access

```bash
# MariaDB
mysql -h 127.0.0.1 -P 3306 -u syracuse -p orange315
# Password: Orange_315_Forever!

# Redis
redis-cli -h 127.0.0.1 -p 6379
```

## Deployment

Each service includes:
- Production-ready configuration
- Health check endpoints
- Logging and monitoring
- Docker/Podman support with static IPs

## Inspired by Saleor

This implementation draws inspiration from Saleor's:
- Domain modeling (Product → ProductVariant maps to SPU → SKU)
- API-first design philosophy
- Database schema patterns with proper indexing
- Service layer architecture
- Entity relationship patterns for e-commerce

## Version History

See `/versions` folder for previous benchmark results and architectural iterations.
