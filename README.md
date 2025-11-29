# Flash Sale Microservices Platform

A **complete flash sale e-commerce platform** with identical functionality implemented in **Python, C#, and Java**. Designed as a foundation for building different flash sale performance optimizations and testing various architectural approaches.

## Overview

This project provides **three independent microservices** implementing flash sale functionality:

1. **Python Service** - FastAPI + SQLAlchemy + MariaDB (InnoDB) + Redis
2. **C# Service** - ASP.NET Core + Entity Framework Core + MariaDB (InnoDB) + Redis  
3. **Java Service** - Spring Boot + JPA + MariaDB (InnoDB) + Redis

## Core Features

All three services implement the same core functionality:

### 📦 **SPU (Standard Product Unit) Management**
- Create and manage product concepts
- Unique slug-based identification
- Product metadata and descriptions

### 🏷️ **SKU (Stock Keeping Unit) Management**
- Product variants with unique SKU codes
- Pricing and cost management
- Weight and inventory tracking

### ⚡ **Flash Sale Events**
- Time-based flash sales with `start_time` and `end_time`
- `total_sale_limit` for maximum items available
- `max_quantity_per_customer` limits
- Real-time status updates (Scheduled → Active → Ended)
- Automatic inventory management

### 📊 **Inventory Management**
- Real-time stock tracking
- Reserved quantity management
- Configurable negative stock policies
- Inventory adjustments and auditing

## Architecture Principles (Inspired by Saleor)

### 🎯 **Domain-Driven Design**
- Clear separation of concerns
- Entity-based modeling
- Business logic encapsulation

### 🚀 **API-First Architecture**
- RESTful APIs with comprehensive documentation
- Structured DTOs/schemas for data transfer
- Validation at API boundaries

### 📈 **Scalability & Performance**
- Redis caching for high-performance reads
- Async operations where possible
- Background tasks for status updates

### 🛡️ **Data Integrity**
- Database constraints and indexes
- Optimistic concurrency handling
- Transaction management

## Important Project Conventions

To ensure consistency and prevent common issues, all developers and LLM agents must adhere to the following conventions:

### 1. ID Generation (Snowflake IDs)

All IDs in this project are **time-based, incrementing UUID-style identifiers**, similar to Twitter's Snowflake IDs. They are not random UUIDs. This means that as time progresses, the IDs should increase. This is a critical architectural aspect of the system.

### 2. Running Tests and Programs

LLM agents **must not** run tests or execute the application. The project owner or developer is responsible for running all programs and tests. The role of the agent is to analyze code, suggest changes, and fix bugs, but not to execute the code.

### 3. Database Schema Migrations

This project follows a **database-first approach**. All database schema changes **must be done manually** through SQL scripts. **Code-first migrations are strictly forbidden.** This is to ensure that all schema changes are deliberate, version-controlled, and approved, as would be the case in a production environment managed by a DevOps team.

### 4. Proactive Bug Resolution

When a bug is identified, do not just fix the single instance. Actively scrutinize the codebase to determine if the same underlying error exists in other parts of the application. Draw inferences from the root cause and apply the fix to all similar cases. This proactive approach ensures a more robust and reliable codebase.

### 5. Python/FastAPI Implementation Patterns

When implementing new endpoints or entities in the Python service, adhere to the following patterns to avoid common pitfalls:

*   **UUIDs in Database Queries**: When filtering by a UUID column (e.g., `id`, `spu_id`), always convert the `UUID` object to a string (`str(uuid_object)`) before passing it to the SQLAlchemy filter. This is necessary because the database stores UUIDs as `CHAR(36)` with hyphens, and the database driver may not correctly format `UUID` objects.

*   **Eagerly Load Relationships for Responses**: In an asynchronous context, SQLAlchemy's lazy loading is disabled. If an endpoint's response model includes a relationship (e.g., an order with its line items), you must explicitly load that relationship *before* returning the object from the endpoint. Use `selectinload` in your queries to prevent `500 Internal Server Error` during response serialization. For example, when returning an `Order` with its `line_items`, query it like this: `select(Order).options(selectinload(Order.line_items)).filter(...)`.

## Service Comparison

| Feature | Python (FastAPI) | C# (ASP.NET Core) | Java (Spring Boot) |
|---------|------------------|-------------------|-------------------|
| **Language** | Python 3.11+ | C# .NET 8 | Java 21+ |
| **Web Framework** | FastAPI | ASP.NET Core | Spring Boot 3.2 |
| **ORM** | SQLAlchemy | Entity Framework Core | Spring Data JPA |
| **Database** | MariaDB (InnoDB) | MariaDB (InnoDB) | MariaDB (InnoDB) |
| **Caching** | Redis | Redis | Redis |
| **Documentation** | OpenAPI/Swagger | Swagger | SpringDoc OpenAPI |
| **Background Tasks** | Celery | Hosted Services | @Scheduled |
| **Object Mapping** | Pydantic | AutoMapper | MapStruct |

## Performance Comparison & Capacity Planning

### Why Different Services for Different Load Profiles

Based on comprehensive benchmarking of `/health` endpoints across all three services, we observed significant performance differences that directly inform capacity planning and inventory allocation strategies:

**Test Environment:**
- **Hardware**: Intel Core Ultra 9 275HX (24 cores), 64GB RAM
- **OS**: WSL2 on Windows
- **Load Test**: wrk with 12 threads, 400 connections, 30 seconds
- **All services**: Single instance, shared database (MariaDB @ 127.0.0.1:3306)

**Raw HTTP Performance (/health endpoint - no database):**

| Service | Requests/sec | Relative Performance | Use Case |
|---------|--------------|---------------------|----------|
| **C# (ASP.NET Core)** | **996,491** | 17.7× faster than Python | High-traffic flash sales, peak load handling |
| **Java (Spring Boot)** | **172,068** | 3.1× faster than Python | Medium-traffic operations, steady state |
| **Python (FastAPI)** | **56,250** | Baseline (1.0×) | Development velocity, rapid iteration |

**Key Findings:**

1. **C# Dominates Raw Throughput**
   - Nearly 1M requests/sec sustained throughput
   - Excellent for handling flash sale traffic spikes
   - .NET runtime optimization provides consistent low latency (avg 756μs)

2. **Java Provides Balanced Performance**
   - 3× faster than Python, stable under load
   - JVM JIT compilation delivers predictable performance
   - Good choice for business-critical services

3. **Python Optimized for Developer Productivity**
   - Fastest development and iteration cycles
   - Still delivers 56K req/s (sufficient for many workloads)
   - Python GIL limits throughput vs compiled languages

**Capacity Planning Implications:**

For a target of **100,000 requests/sec** across the platform:

| Service | Instances Needed | Inventory Allocation Strategy |
|---------|------------------|-------------------------------|
| **C#** | 1 instance (996K/s) | Allocate 60-70% of total inventory - handles flash sale peaks |
| **Java** | 1 instance (172K/s) | Allocate 20-25% of total inventory - steady-state operations |
| **Python** | 2 instances (56K/s each) | Allocate 10-15% of total inventory - development/testing |

**Why This Matters for Flash Sales:**

During high-traffic flash sale events (e.g., limited quantity drops, time-sensitive promotions):
- **C# instances** handle the initial traffic surge (first 60 seconds)
- **Java instances** provide reliable secondary capacity
- **Python instances** handle overflow and provide deployment flexibility

### Order API Performance (Database Transactions)

**Test Configuration:**
- **Test Data**: 500 SKUs with 10,000 stock each (5M total inventory)
- **Load Test**: wrk with 12 threads, 100 connections, 30 seconds
- **Operations**: Full ACID transactions (orders + line_items + inventory updates)
- **Database**: Shared MariaDB instance (127.0.0.1:3306)
- **Status**: ✅ All three services fully functional with wrk stress tests

**Measured Results:**

| Service | Throughput | Latency (avg) | Database Writes | Success Rate |
|---------|-----------|---------------|-----------------|--------------|
| **Python (FastAPI)** | 1,590 req/s | 65.96ms | **47,852 orders** | 99.98% |
| **Java (Spring Boot)** | 2,074 req/s | 51.33ms | **51,264 orders** | 83.8% |
| **C# (ASP.NET Core)** | 3,780 req/s | 33.79ms | **94,549 orders** | 84.6% |

**Actual Order Creation Throughput:**

| Service | Orders/sec | vs Python | vs Java |
|---------|------------|-----------|---------|
| **Python** | 1,595 orders/sec | baseline | - |
| **Java** | 1,742 orders/sec | +9.2% | baseline |
| **C#** | 3,202 orders/sec | +100.7% (2×) | +83.9% |

**Key Findings:**

1. **Database is the Bottleneck (Not Application Code)**
   - Performance gap narrows from 10-17× (/health) to just 2× (orders)
   - C# loses 311× performance, Java loses 99×, Python loses 60×
   - Connection pool exhaustion observed across all services
   - Higher throughput services show more DB-related failures

2. **All Services Now Fully Compatible**
   - Fixed JSON property naming (snake_case) in Java and C#
   - All services accept wrk Lua script requests
   - Shared database schema with identical column names and types
   - Load balancer ready with zero conflicts

3. **Performance vs Reliability Trade-off**
   - Python: Lower throughput (1,595/s) but highest success rate (99.98%)
   - Java: Medium throughput (1,742/s) with 83.8% success
   - C#: Highest throughput (3,202/s) with 84.6% success
   - Failures correlate with database connection limits

**Production Capacity (Proven Performance):**

| Service | Proven Throughput | Instances for 10K orders/sec |
|---------|-------------------|------------------------------|
| **Python** | 1,600 orders/sec | 7 instances |
| **Java** | 1,750 orders/sec | 6 instances |
| **C#** | 3,200 orders/sec | 3-4 instances |

*Note: Database optimization required for sustained 10K+ orders/sec (increase max_connections, optimize pools)*

**Database Bottleneck Evidence:**

The performance reduction from /health to Order API proves database transactions dominate:
- Python: 95K → 1.6K req/s (60× slower)
- Java: 172K → 1.7K req/s (99× slower)
- C#: 996K → 3.2K req/s (311× slower)

The faster the framework, the more the database bottlenecks it. This confirms database I/O and ACID transaction commits as the limiting factor, not application code.

**Running Order API Stress Tests:**

```bash
# Step 1: Generate test data (run once)
cd python-service
python setup_test_data.py 100 5 10000

# Step 2: Test Python
cd python-service
./START_SERVER_OPTIMIZED.sh
./benchmark_orders.sh

# Step 3: Test Java
cd java-service
mvn spring-boot:run
# In another terminal:
cd java-service
wrk -t12 -c100 -d30s -s wrk_order_script.lua http://localhost:8081/api/v1/orders

# Step 4: Test C#
cd csharp-service
dotnet run --urls "http://0.0.0.0:8082"
# In another terminal:
cd csharp-service
wrk -t12 -c100 -d30s -s wrk_order_script.lua http://localhost:8082/api/v1/orders
```

**Database Schema Compatibility:**
- ✅ All services use snake_case JSON properties (customer_email, sku_id)
- ✅ All services use snake_case database columns (order_number, customer_email, created_at)
- ✅ All services use CHAR(36) UUIDs with hyphens
- ✅ All services use identical table names and foreign keys
- ✅ **Load balancer ready**: Clients cannot distinguish which service handled their request

## Quick Start

### Prerequisites

Before running the services, ensure you have:

**Database & Cache:**
- **MariaDB 10.6.22+** running on `127.0.0.1:3306`
  - Database: `orange315`
  - User: `syracuse`
  - Password: `Orange_315_Forever!`
- **Redis 6.0.16+** running on `127.0.0.1:6380`

**Language Runtimes:**
- **Python 3.11+** (for Python service)
- **Java 21+** (for Java service)
- **.NET 8 SDK** (for C# service)

**Tools:**
- **wrk** - HTTP benchmarking tool (for performance testing)
- **Maven** - Java build tool
- **Git** - Version control

### Service Ports

| Service | Port | Health Check | API Docs |
|---------|------|--------------|----------|
| **Python** | 8000 | http://localhost:8000/health | http://localhost:8000/docs |
| **Java** | 8081 | http://localhost:8081/health | http://localhost:8081/swagger-ui.html |
| **C#** | 8082 | http://localhost:8082/health | http://localhost:8082/swagger |

### Starting Services

All three services share the same database and can run simultaneously.

#### Python Service
```bash
cd python-service
./START_SERVER_OPTIMIZED.sh
# Or manually:
# pip install -r requirements.txt
# uvicorn app.main:app --reload
```

#### Java Service
```bash
cd java-service
./START_SERVER.sh
# Or manually:
# mvn spring-boot:run
```

#### C# Service
```bash
cd csharp-service
./START_SERVER.sh
# Or manually:
# dotnet run --urls "http://0.0.0.0:8082"
```

### Testing Health Endpoints

```bash
# Test all services at once
curl http://localhost:8000/health  # Python - should return "200 OK"
curl http://localhost:8081/health  # Java - should return "200 OK"
curl http://localhost:8082/health  # C# - should return "200 OK"
```

### Testing Order API

All services expose the same REST API endpoints:

**Common Endpoints:**
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders` - List orders
- `GET /api/v1/orders/{id}` - Get order by ID

**Example - Create Order:**
```bash
# Get a test SKU ID (after running setup_test_data.py)
SKU_ID=$(head -1 /tmp/stress_test_sku_ids.txt)

# Python
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_email\": \"test@example.com\",
    \"customer_name\": \"Test User\",
    \"currency\": \"USD\",
    \"line_items\": [{
      \"sku_id\": \"$SKU_ID\",
      \"quantity\": 2
    }]
  }"

# Java
curl -X POST http://localhost:8081/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_email\": \"test@example.com\",
    \"customer_name\": \"Test User\",
    \"currency\": \"USD\",
    \"line_items\": [{
      \"sku_id\": \"$SKU_ID\",
      \"quantity\": 2
    }]
  }"

# C#
curl -X POST http://localhost:8082/api/v1/orders \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_email\": \"test@example.com\",
    \"customer_name\": \"Test User\",
    \"currency\": \"USD\",
    \"line_items\": [{
      \"sku_id\": \"$SKU_ID\",
      \"quantity\": 2
    }]
  }"
```

### Database Connection

All services connect to the same MariaDB instance:
- **Host:** 127.0.0.1:3306
- **Database:** orange315
- **User:** syracuse
- **Password:** Orange_315_Forever!

You can verify orders created by any service:
```bash
mysql -h 127.0.0.1 -P 3306 -u syracuse -pOrange_315_Forever! -D orange315 \
  -e "SELECT id, order_number, customer_email, total_amount, status FROM orders ORDER BY created_at DESC LIMIT 5;"
```

#### Java Service
```bash
cd java-service
mvn clean compile
mvn spring-boot:run
# API: http://localhost:8080/swagger-ui.html
```

## Database Schema

All services implement the same logical data model:

**Core Models:**
- **SPU (Standard Product Unit)**: Product catalog entries
- **SKU (Stock Keeping Unit)**: Product variants with pricing  
- **Inventory**: Stock levels and reservations
- **Flash Sale Events**: Time-limited promotional campaigns
- **Orders**: Customer purchase records (regular + flash sale)
- **Order Line Items**: Individual items within orders
- **Payments**: Payment transaction records

**All IDs**: UUID format (CHAR(36)) for distributed generation and cross-service compatibility

## API Endpoints

All services expose the same REST API structure:

### SPU Endpoints
- `GET /api/v1/spus` - List SPUs
- `POST /api/v1/spus` - Create SPU
- `GET /api/v1/spus/{id}` - Get SPU by ID
- `PUT /api/v1/spus/{id}` - Update SPU
- `DELETE /api/v1/spus/{id}` - Delete SPU

### SKU Endpoints
- `GET /api/v1/skus` - List SKUs
- `POST /api/v1/skus` - Create SKU
- `GET /api/v1/skus/{id}` - Get SKU by ID
- `PUT /api/v1/skus/{id}` - Update SKU
- `DELETE /api/v1/skus/{id}` - Delete SKU

### Flash Sale Endpoints
- `GET /api/v1/flash-sales` - List flash sale events
- `POST /api/v1/flash-sales` - Create flash sale event
- `GET /api/v1/flash-sales/{id}` - Get flash sale by ID
- `PUT /api/v1/flash-sales/{id}` - Update flash sale
- `POST /api/v1/flash-sales/{id}/purchase` - Purchase from flash sale
- `DELETE /api/v1/flash-sales/{id}` - Delete flash sale

### Inventory Endpoints
- `GET /api/v1/inventory/{sku_id}` - Get inventory for SKU
- `PUT /api/v1/inventory/{sku_id}` - Update inventory
- `POST /api/v1/inventory/{sku_id}/adjust` - Adjust inventory quantity
- `POST /api/v1/inventory/{sku_id}/reserve` - Reserve inventory
- `POST /api/v1/inventory/{sku_id}/release` - Release reserved inventory

## Business Logic

### Flash Sale State Management
Flash sales automatically transition through states:
- **Scheduled** → **Active** (when current time >= start_time)
- **Active** → **Ended** (when current time >= end_time OR sold_quantity >= total_sale_limit)
- **Any State** → **Cancelled** (manual cancellation)

### Inventory Management
- **Available Quantity** = Total Quantity - Reserved Quantity
- **Reservation System** prevents overselling
- **Fulfillment Process** reduces both reserved and total quantities

### Concurrency Handling
- Database-level constraints prevent duplicate slugs/SKU codes
- Optimistic locking for inventory updates
- Transaction boundaries for multi-step operations

## Technology Choices Rationale

### Why These Tech Stacks?

**Python/FastAPI**: Modern async framework, excellent for rapid development, strong typing with Pydantic
**C#/ASP.NET Core**: Enterprise-grade performance, excellent tooling, strong typing system
**Java/Spring Boot**: Battle-tested ecosystem, excellent for complex business logic, comprehensive features

### Why MariaDB with InnoDB for Flash Sales?

**MariaDB with InnoDB** is specifically chosen for optimal flash sale performance:
- **Row-level locking**: Prevents overselling with minimal contention during high concurrency
- **MVCC (Multi-Version Concurrency Control)**: Allows multiple reads while writes are happening
- **ACID compliance**: Ensures data integrity during flash sale inventory updates
- **Performance optimizations**: Optimized buffer pool, redo log settings for high-throughput scenarios
- **Proven at scale**: Battle-tested for e-commerce workloads and flash sale scenarios

### Common Infrastructure
- **MariaDB with InnoDB**: Optimized for flash sale performance with row-level locking, ACID compliance, and excellent concurrency handling for high-traffic scenarios. InnoDB's MVCC (Multi-Version Concurrency Control) prevents overselling in flash sale scenarios
- **Redis**: High-performance caching and session storage for rapid data access
- **UUID Generation**: Distributed UUID generation for zero conflicts across services

## Testing Flash Sale Functionality

### Regular Order Flow
```bash
# 1. Create an order
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test Customer", 
    "currency": "USD",
    "line_items": [
      {
        "sku_id": "650e8400-e29b-41d4-a716-446655440001",
        "quantity": 1
      }
    ]
  }'

# 2. Process payment (mock)
curl -X POST "http://localhost:8000/api/v1/orders/{order_id}/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 999.00,
    "currency": "USD",
    "payment_method": "credit_card"
  }'
```

### Flash Sale Testing (Overselling Prevention)
```bash
# 1. Get active flash sales
curl http://localhost:8000/api/v1/flash-sales

# 2. Purchase from flash sale 
curl -X POST "http://localhost:8000/api/v1/flash-sales/{flash_sale_id}/purchase" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 1
  }'

# 3. Test overselling protection
curl -X POST "http://localhost:8000/api/v1/flash-sales/{flash_sale_id}/purchase" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 25
  }'
# Should fail with insufficient quantity error

# 4. Test per-customer limits  
curl -X POST "http://localhost:8000/api/v1/flash-sales/{flash_sale_id}/purchase" \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 3
  }'
# Should fail with max quantity per customer error (limit is 2)
```

## Database Access

```bash
# Connect to MariaDB
mysql -h 127.0.0.1 -P 3306 -u syracuse -p orange315
# Password: Orange_315_Forever!

# Connect to Redis
redis-cli -h 127.0.0.1 -p 6380
```

## Deployment

Each service includes:
- Production-ready configuration
- Health check endpoints
- Logging and monitoring setup
- Docker support (ready for containerization)

## Inspired by Saleor

This implementation takes inspiration from Saleor's:
- **Domain modeling** approach (Product → ProductVariant mapping to SPU → SKU)
- **API-first design** philosophy
- **Database schema patterns** with proper indexing and constraints
- **Service layer architecture** with clear separation of concerns
- **Entity relationship patterns** for e-commerce concepts

## Next Steps

To extend these services, consider adding:
- User authentication and authorization
- Order management integration
- Payment processing
- Real-time notifications
- Metrics and analytics
- Rate limiting and throttling
- Distributed tracing