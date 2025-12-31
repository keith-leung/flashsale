# Flash Sale Microservices Platform

A **complete flash sale e-commerce platform** with identical functionality implemented in **Python, C#, and Java**. Designed for **performance testing and architectural comparison** across different optimization strategies.

> **⚠️ FOR ALL AGENTS:** Read `/versions/CONVENTIONS.md` FIRST before any action. All policies, credentials, and conventions are documented there.

## 🎯 Project Objective

**Primary Challenge**: Handle **100,000 order requests within 1 second** without 503 errors or overselling.

This platform was built to solve a critical e-commerce challenge: implementing a generic and scalable system to support high-traffic "Flash Sale" events with absolute data integrity.

### Business Requirements

1. **Flash Sale Campaign Data Model**
   - **CRITICAL**: Campaigns are **SPU-level** (product concept), NOT SKU-level (variants)!
   - **Business Example**: Manager creates campaign for "iPhone 16" (SPU) with 100K total_sale_limit
   - **Customer Reality**: Customers order "iPhone 16 Black 512GB" or "iPhone 16 Silver 128GB" (SKUs)
   - **Campaign Tracking**: `total_sale_limit` applies across **ALL SKUs** under that SPU (100K total across all colors/storage variants)
   - **Why SPU Matters**: Without SPU grouping, managers would need separate campaigns for every variant - impossible to manage at scale!
   - Support multiple, distinct flash sale campaigns simultaneously
   - `start_time` and `end_time`: Temporal boundaries for the campaign
   - Real-time status tracking (Not Started → Active → Sold Out/Ended)

2. **Extreme Concurrency Handling**
   - A single campaign with 1,000-item limit must correctly handle 100,000 purchase attempts in the first second
   - Zero overselling - perfect inventory consistency
   - No 503 errors under peak load

3. **Backward-Compatible Order API**
   - **CRITICAL**: Frontends ALWAYS use `/api/v1/orders` for ALL purchases (regular AND flash sale)
   - The frontend never calls flash sale endpoints directly
   - The backend automatically detects if a SKU is part of an active flash sale campaign
   - Same endpoint, same request format - transparent to the client
   - Zero frontend changes required when adding/removing flash sales

4. **High-Performance Sale Status API**
   - Return real-time campaign state: "Not Started", "Active", "Sold Out", "Ended"
   - Handle significantly higher read load than the purchase API (10-100× more status checks than purchases)
   - Zero impact on transaction performance

5. **Dual-Level Inventory Validation**
   - **SPU-level (Campaign Limit)**: Campaign's `total_sale_limit` not exceeded across ALL variants
     - Example: iPhone 16 campaign with 100K limit - tracks total across all colors/storage
   - **SKU-level (Inventory Stock)**: Individual variant's inventory > 0
     - Example: "iPhone 16 Black 512GB" has 5,000 units in stock
   - **Both conditions must be met**:
     - Order "iPhone 16 Black 512GB" (qty: 2) → Check campaign (100K limit) AND SKU inventory (5,000 stock)
     - If campaign has 99,999 sold: Order succeeds (within campaign limit)
     - If SKU inventory is 1: Order fails (insufficient stock for qty=2)

6. **Distributed System Requirements**
   - Absolute data integrity across multiple load-balanced servers
   - Perfect consistency for both SPU-level campaign limits and SKU-level inventory
   - Horizontal scalability (add more servers → handle more load)
   - High availability (no single point of failure)

### Why This Architecture?

This repository implements **multiple architectural variants** to test different approaches to solving the same challenge:
- **Variant Y (Baseline)**: Database-heavy, minimal caching - establishes the performance floor
- **Variant X (Redis-Optimized)**: Aggressive caching with batch prefetch - tests cache effectiveness
- **Future Variants**: Read replicas, async writes, sharding - exploring scalability patterns

Each variant must meet the same business requirements while using different technical strategies.

## 🏗️ Multi-Variant Architecture

Due to Podman 3.4.4 limitations with static IP allocation, **each architectural variant runs in a dedicated WSL instance** for clean isolation and fair comparison.

### This WSL Instance: Variant Y (Baseline)

**Architecture:** Standard database-heavy with minimal caching
- Direct database queries for all operations
- Basic Redis connection (not actively used for caching)
- 4-7 database round-trips per order (SELECT SKU, SELECT Inventory, UPDATE Inventory, INSERT Order, INSERT Line Items)
- **Purpose:** Baseline performance metrics for comparison

### Other Variants (Separate WSL Instances)

**Variant X (Redis-Optimized):**
- Aggressive cache-aside pattern with batch prefetch
- SKU/Inventory data cached in Redis
- Reduced database queries (2-3 per order vs 4-7)
- Enhanced Redis resources (6 CPUs, 6GB RAM vs 2 CPUs, 2GB RAM)

**Future Variants:**
- Read replicas for read-heavy workloads
- Write-optimized with async inventory updates
- Sharded database architecture

**Setup Guide:** See [DEPLOYMENT.md](DEPLOYMENT.md) for instructions on duplicating this WSL for other variants.

## 📊 Baseline Performance Results (Variant Y - Dec 27, 2025)

### Test Environment

**Hardware & CPU Pinning:**
```
Intel Core Ultra 9 275HX (8 P-cores + 16 E-cores)

P-Cores (0-7) - Middleware:
├─ MariaDB: 8 cores, 16GB RAM
├─ Redis:   2 cores, 2GB RAM
└─ Nginx:   1 core, 512MB RAM

E-Cores (8-23) - Applications:
├─ Python:  4 cores, 4GB RAM
├─ Java:    4 cores, 4GB RAM
└─ C#:      4 cores, 4GB RAM
```

**Network Configuration:**
- Podman network: 10.88.0.0/16 (static IP allocation)
- MariaDB: 10.88.0.2:3306
- Redis: 10.88.0.3:6379
- Python: 10.88.0.4:8000 (host: 8000)
- Java: 10.88.0.5:8080 (host: 8081)
- C#: 10.88.0.6:80 (host: 8082)
- Nginx: 10.88.0.7:443 (host: 8443)

**Test Data:**
- 500 SPUs (Standard Product Units)
- 2,500 SKUs (Stock Keeping Units)
- 25M total stock (10,000 per SKU)

**Load Test Parameters:**
```bash
wrk -t12 -c100 -d30s
# 12 threads, 100 concurrent connections, 30 seconds duration
```

### Health Check Results

#### Direct Access (Service → Response)

**Commands:**
```bash
curl http://localhost:8000/health  # Python
curl http://localhost:8081/health  # Java
curl http://localhost:8082/health  # C#
```

**Results:**
| Service | Status |
|---------|--------|
| Python (FastAPI) | ✅ 200 OK |
| Java (Spring Boot) | ✅ 200 OK |
| C# (ASP.NET Core) | ✅ 200 OK |

#### Via Nginx Load Balancer

**Commands:**
```bash
curl -k https://localhost:8443/python/health   # Direct to Python via Nginx
curl -k https://localhost:8443/java/health     # Direct to Java via Nginx
curl -k https://localhost:8443/csharp/health   # Direct to C# via Nginx
```

**Results:**
| Service | Status |
|---------|--------|
| Python via Nginx | ✅ 200 OK |
| Java via Nginx | ✅ 200 OK |
| C# via Nginx | ✅ 200 OK |

### Order API Performance (Direct Access)

#### Test Commands

**Python:**
```bash
wrk -t12 -c100 -d30s -s python-service/wrk_order_script.lua \
  http://localhost:8000/api/v1/orders
```

**Java:**
```bash
wrk -t12 -c100 -d30s -s java-service/wrk_order_script.lua \
  http://localhost:8081/api/v1/orders
```

**C#:**
```bash
wrk -t12 -c100 -d30s -s csharp-service/wrk_order_script.lua \
  http://localhost:8082/api/v1/orders
```

#### Benchmark Results (Service → Database)

| Service | Throughput | Latency (avg) | Total Requests | Success Rate | vs Python |
|---------|-----------|---------------|----------------|--------------|-----------|
| **Java (Spring Boot)** | **2,764 req/s** | **24.94ms** | 82,920 | 100% | **3.6× faster** |
| **C# (ASP.NET Core)** | **2,328 req/s** | **38.98ms** | 69,840 | 100% | **3.0× faster** |
| **Python (FastAPI)** | 767 req/s | 62.49ms | 23,010 | 100% | baseline |

### Nginx Load Balancer Performance

#### Health Endpoint Performance

**Test Command:**
```bash
wrk -t12 -c25 -d30s --latency https://localhost:8443/health
```

**Results:**
| Metric | Value |
|--------|-------|
| **Throughput** | 10,106 req/s |
| **Latency (avg)** | 32.24ms |
| **Optimal Concurrency** | `-c25` |
| **Success Rate** | 100% |

#### Order Processing Performance

**Test Command:**
```bash
wrk -t4 -c50 -d30s --latency -s /tmp/order_benchmark.lua \
  https://localhost:8443/api/v1/orders
```

**Results (Client → Nginx → Services → Database):**

| Metric | Value |
|--------|-------|
| **Throughput** | 1,113 req/s |
| **Latency (avg)** | 68.32ms |
| **Optimal Concurrency** | `-t4 -c50` |
| **Success Rate** | 90.8% |
| **Load Distribution** | Round-robin (Python, Java, C#) |

**Nginx Round-Robin Bottleneck Analysis:**
- **Critical Finding:** Combined throughput (1,113 req/s) constrained by slowest service (Python: 694 req/s)
- Optimal concurrency must match Python's capacity, not combined capacity of all services
- Round-robin distributes load evenly, but Python creates backpressure when saturated
- Error rate (9.2%) indicates Python returning 500 errors under load
- **Production Implication:** Heterogeneous service pools require dedicated pools per service type
- Combining fast services (Java: 2,764 req/s, C#: 2,328 req/s) with slow services (Python: 694 req/s) in same pool reduces overall throughput by ~80%

### Key Findings

1. **Java Performance Leader**
   - 2,764 req/s throughput with 25ms latency
   - 100% success rate under load
   - Most cost-effective for production (4 instances for 10K req/s)

2. **C# Strong Performance**
   - 2,328 req/s with 39ms latency
   - 100% success rate
   - Good balance (4-5 instances for 10K req/s)

3. **Python Developer Productivity**
   - 767 req/s with 62ms latency
   - 100% success rate (excellent reliability)
   - Requires 13-14 instances for 10K req/s

4. **Database I/O Bottleneck**
   - All services perform 4-7 database queries per order
   - Performance gap narrows from 10.7× (/health) to 3.6× (orders)
   - Database transactions dominate execution time
   - Proves application code is not the bottleneck

5. **CPU Pinning Effectiveness**
   - E-cores (8-23) sufficient for I/O-bound application workloads
   - P-cores (0-7) critical for MariaDB I/O performance
   - Middleware benefits significantly from P-core allocation

6. **Static IP Reliability**
   - 100% success rates on direct access
   - Resolves Podman 3.4.4 DNS resolution issues
   - Consistent connectivity across services

7. **Nginx Round-Robin Bottleneck (Critical Finding)**
   - Health endpoint: 10,106 req/s (optimal: `-c25`)
   - Order endpoint: 1,113 req/s (optimal: `-t4 -c50`) with 90.8% success rate
   - **Bottleneck Behavior:** Combined throughput constrained by slowest service (Python)
   - Optimal concurrency matches Python capacity (694 req/s), not combined capacity (5,551 req/s)
   - Mixing heterogeneous services (Python + Java + C#) reduces throughput by ~80%
   - **Production Recommendation:** Use dedicated pools per service type or language
   - SSL termination adds ~32ms latency overhead for health, ~68ms for orders

8. **Production Capacity Planning**
   - Java: Most cost-effective at 2,764 req/s per instance
   - C#: Good balance at 2,328 req/s per instance
   - Python: Development velocity advantage, 767 req/s per instance

### Raw Framework Performance Analysis (Upper Bound Limits)

Stress testing the `/health` endpoint revealed the theoretical maximum throughput for each framework configuration. This establishes the "speed of light" for each language before business logic and database I/O are introduced.

| Service | Architecture | Peak Throughput | Optimal Concurrency | Limiting Factor |
| :--- | :--- | :--- | :--- | :--- |
| **C#** | ASP.NET Core 8 | **~438,996 req/s** | `-c 600` | Hardware/Network |
| **Java** | Spring Boot 3.2 | **~190,843 req/s** | `-c 200` | Framework Overhead |
| **Python** | FastAPI + Uvicorn | **~40,869 req/s** | `-c 100` | Middleware Overhead |

**Key Insights:**
1.  **C# Scalability**: ASP.NET Core is the undisputed performance leader, handling nearly **439k requests per second** on a single instance. It scales linearly up to `c600` concurrency.
2.  **Java Efficiency**: Spring Boot delivers excellent performance (~191k req/s), peaking at `c200`. Beyond this, thread contention begins to slightly degrade throughput.
3.  **Python Plateau**: FastAPI hits a hard ceiling around **41k req/s** at relatively low concurrency (`c100`). This is due to the per-request overhead of the global middleware (UUID generation, async context switching), even when logging is skipped.

**Optimal Benchmark Settings:**
To reproduce these peak numbers, use the following `wrk` configurations:
*   **C#**: `wrk -t12 -c600 -d30s http://localhost:8082/health`
*   **Java**: `wrk -t12 -c200 -d30s http://localhost:8081/health`
*   **Python**: `wrk -t12 -c100 -d30s http://localhost:8000/health`

**Concurrency Tuning Methodology:**
These optimal concurrency values were determined by testing multiple levels (e.g., `-c25`, `-c50`, `-c100`, `-c200`, `-c400`, `-c1000`) and observing where throughput plateaus. Each service has a different sweet spot where additional concurrent connections no longer improve req/s and may even degrade performance due to increased contention. Always perform a concurrency sweep when benchmarking to find the true optimal configuration for your specific hardware and workload.

## 🔍 Order Procedure Analysis (Why Database is the Bottleneck)

The order procedure is **intentionally "chatty"** with the database (multiple round-trips) to simulate realistic, complex transactional workloads.

### Database Operations Per Order

**Minimum 4-7 separate database interactions:**

1. **INSERT Order Header** (1 query)
2. **SELECT SKU + Inventory** (1 query per line item)
3. **UPDATE Inventory** (1 query per line item)
4. **INSERT Line Items** (batch or individual)
5. **UPDATE Order Totals** (1 query)

**Example with 3 line items:** 1 + 3 + 3 + 1 + 1 = **9 database queries**

### Python Implementation (`app/api/endpoints/orders.py`)

```python
# DB Query #1: Insert Order Header
order = Order(order_number=order_number, ...)
db.add(order)
await db.flush()  # Get order ID immediately

# DB Queries #2-N: Loop through line items
for item_data in order_data.line_items:
    # SELECT SKU & Inventory (1 query per item)
    result = await db.execute(
        select(SKU).filter(SKU.id == str(item_data.sku_id))
    )
    sku = result.scalar_one_or_none()

    # Modify inventory in memory
    sku.inventory.reserve_quantity(item_data.quantity)

    # Prepare line item for batch insert
    line_items_to_add.append(OrderLineItem(...))

# DB Query #N+1: Commit transaction
db.add_all(line_items_to_add)
await db.commit()  # Batch UPDATE inventory + INSERT line items
```

### Java Implementation (`OrderService.java`)

```java
// DB Query #1: Insert Order Header
order = orderRepository.save(order);

// DB Queries #2-N: Loop through line items
for (OrderLineItemCreateDto itemDto : createDto.getLineItems()) {
    // SELECT SKU & Inventory (1 query per item)
    Sku sku = skuRepository.findByIdWithInventoryAndSpu(
        itemDto.getSkuId()
    );

    // Reserve inventory (tracked by JPA)
    sku.getInventory().reserveQuantity(itemDto.getQuantity());

    // Save per item (potential DB query each iteration)
    inventoryRepository.save(sku.getInventory());
    orderLineItemRepository.save(lineItem);
}

// DB Query #N+1: Final update
orderRepository.save(order);
```

### C# Implementation (`OrderService.cs`)

```csharp
// DB Query #1: Insert Order Header
_context.Orders.Add(order);
await _context.SaveChangesAsync();

// DB Queries #2-N: Loop through line items
foreach (var itemDto in dto.LineItems)
{
    // SELECT SKU & Inventory (1 query per item)
    var sku = await _context.Skus
        .Include(s => s.Inventory)
        .FirstOrDefaultAsync(...);

    // Reserve inventory (tracked by EF Core)
    sku.Inventory.ReserveQuantity(itemDto.Quantity);
    _context.OrderLineItems.Add(new OrderLineItem { ... });
}

// DB Query #N+1: Commit transaction
await _context.SaveChangesAsync();
await transaction.CommitAsync();
```

### Performance Impact

This "chatty" design explains why:
- C# loses 189× performance from /health (439K) to orders (2.3K)
- Java loses 69× performance from /health (191K) to orders (2.8K)
- Python loses 53× performance from /health (41K) to orders (767)

**The faster the framework, the more database latency dominates.**

## 🎯 Project Goal

The ultimate destination is to **optimize order flash sale performance to approach the raw throughput of the `/health` endpoint**. We achieve this by experimenting with different architectural variants (e.g., caching strategies, async processing) and measuring the "performance gap" between raw framework overhead and complex business logic.

## 🚀 Manual Reproduction Procedure (Quick Start)

Follow these phases strictly to reproduce the baseline results and verify the environment.

### Prerequisites

**Required Services:**
- Podman 3.4.4+ or Docker 20.10+
- wrk (HTTP benchmarking tool)

**All dependencies containerized:**
- MariaDB 10.11 (included in docker-compose.yml)
- Redis 6.0+ (included in docker-compose.yml)
- Nginx (included in docker-compose.yml)

### Start All Services

```bash
# Start entire stack
podman-compose up -d

# Verify containers are running
podman ps

# Check service health (Basic Connectivity)
curl http://localhost:8000/health  # Python
curl http://localhost:8081/health  # Java
curl http://localhost:8082/health  # C#
curl -k https://localhost:8443/python/health  # Via Nginx
```

### Phase 1: Environment & Data Setup

1. **Generate Test Data (Critical Step)**
   Creates 2,500 SKUs with 25M total stock.
   ```bash
   podman exec flash-python python /app/setup_test_data.py 500 5 10000
   ```

2. **Extract SKU IDs**
   Required for the benchmark scripts to know which items to purchase.
   ```bash
   podman cp flash-python:/tmp/stress_test_sku_ids.txt /tmp/stress_test_sku_ids.txt
   ```

### Phase 2: Verify Codebase Integrity

Run the Python unit tests to ensure business logic (Inventory, Orders, SKU) is correct before stressing the system. This serves as the "Source of Truth" for logic correctness.

```bash
podman exec flash-python python -m pytest
# Expected: ===== 29 passed in X.Xs =====
```

### Phase 3: Raw Framework Performance (Direct /health)

Measure maximum throughput with minimal logic to establish the theoretical ceiling.

1. **Python (Direct):** ~41k req/s
   ```bash
   wrk -t12 -c100 -d30s --latency http://localhost:8000/health
   ```

2. **Java (Direct):** ~191k req/s
   ```bash
   wrk -t12 -c200 -d30s --latency http://localhost:8081/health
   ```

3. **C# (Direct):** ~439k req/s
   ```bash
   wrk -t12 -c600 -d30s --latency http://localhost:8082/health
   ```

### Phase 4: Order Processing (Direct Access)

Measure application logic + DB performance (bypassing load balancer). This is the baseline "business logic" performance.

1. **Python (Direct):** ~767 req/s
   ```bash
   wrk -t12 -c50 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8000/api/v1/orders
   ```

2. **Java (Direct):** ~2,764 req/s
   ```bash
   wrk -t12 -c75 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8081/api/v1/orders
   ```

3. **C# (Direct):** ~2,328 req/s
   ```bash
   wrk -t12 -c25 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8082/api/v1/orders
   ```

### Phase 5: "Real Client" Benchmarks (Via Nginx)

Simulate external clients hitting the unified gateway (SSL termination + routing).

**A. Health Checks via Nginx**

1. **Python via Nginx:**
   ```bash
   bash python-service/benchmark_health.sh https://localhost:8443/python/health
   ```

2. **Java via Nginx:**
   ```bash
   wrk -t12 -c400 -d30s --latency https://localhost:8443/java/health
   ```

3. **C# via Nginx:**
   ```bash
   wrk -t12 -c400 -d30s --latency https://localhost:8443/csharp/health
   ```

**B. Order Processing via Nginx (Round-Robin)**

Tests aggregate performance of all services mixed together.

```bash
bash python-service/benchmark_orders.sh https://localhost:8443/api/v1/orders
# Expected: ~2,100 req/s (average of all three + Nginx overhead)
```

### Manual Order Creation (Testing)

```bash
# Get a test SKU ID
SKU_ID=$(head -1 /tmp/stress_test_sku_ids.txt)

# Create order via Python
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
```

### Verify Orders in Database

```bash
# Connect to MariaDB container
podman exec -it flash-mariadb mysql -u syracuse -pOrange_315_Forever! orange315

# Check recent orders
SELECT id, order_number, customer_email, total_amount, status
FROM orders
ORDER BY created_at DESC
LIMIT 10;
```

## 📦 Core Features

All three services implement identical functionality:

### SPU (Standard Product Unit) Management
- Product concepts with unique slug-based identification
- Metadata and descriptions
- Variants (SKUs) association

### SKU (Stock Keeping Unit) Management
- Product variants with unique SKU codes
- Pricing and cost management
- Weight and inventory tracking

### Flash Sale Events
- Time-based sales (`start_time`, `end_time`)
- Sale limits (`total_sale_limit`)
- Customer quantity restrictions (`max_quantity_per_customer`)
- Automatic state transitions (Scheduled → Active → Ended)

### Inventory Management
- Real-time stock tracking
- Reserved quantity management
- Overselling prevention
- Inventory adjustments and auditing

### Order Processing
- Full ACID transactions
- Multi-item orders with line items
- Inventory reservation and fulfillment
- Payment tracking

## 🏛️ Architecture Principles

### Domain-Driven Design
- Clear separation of concerns
- Entity-based modeling
- Business logic encapsulation

### API-First Architecture
- RESTful APIs with OpenAPI/Swagger
- Consistent DTOs/schemas across services
- Validation at API boundaries

### Database-First Approach
- Manual SQL migrations (no code-first)
- Deliberate schema changes
- Production-ready practices

### Scalability & Performance
- Redis caching layer
- Async operations
- Background tasks
- Connection pooling

### Data Integrity
- Database constraints and indexes
- Optimistic locking for inventory
- Transaction management
- ACID compliance

## 🛠️ Service Comparison

| Feature | Python (FastAPI) | C# (ASP.NET Core) | Java (Spring Boot) |
|---------|------------------|-------------------|-------------------|
| **Language** | Python 3.11+ | C# .NET 8 | Java 21+ |
| **Web Framework** | FastAPI | ASP.NET Core | Spring Boot 3.2 |
| **ORM** | SQLAlchemy | EF Core | Spring Data JPA |
| **Database** | MariaDB (InnoDB) | MariaDB (InnoDB) | MariaDB (InnoDB) |
| **Caching** | Redis | Redis | Redis |
| **Documentation** | OpenAPI/Swagger | Swagger | SpringDoc |
| **Background Tasks** | Celery | Hosted Services | @Scheduled |
| **Object Mapping** | Pydantic | AutoMapper | MapStruct |

## 📋 Important Project Conventions

### 1. ID Generation (Snowflake IDs)

All IDs are **time-based, incrementing UUID-style identifiers** (like Twitter Snowflake IDs). They are NOT random UUIDs - IDs increase over time.

### 2. Database Schema Migrations

**Database-first approach only.** All schema changes via manual SQL scripts. Code-first migrations are forbidden.

### 3. Proactive Bug Resolution

When fixing a bug, scan the entire codebase for similar patterns and apply the fix everywhere.

### 4. Python/FastAPI Patterns

- **UUIDs in Queries**: Convert UUID objects to strings before database queries (`str(uuid_object)`)
- **Eager Loading**: Use `selectinload()` for relationships in async contexts to prevent lazy loading errors

```python
# Good
select(Order).options(selectinload(Order.line_items)).filter(...)

# Bad (will cause 500 errors)
select(Order).filter(...)  # line_items will fail to load
```

## 🔗 API Endpoints

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

### Flash Sale Campaign Endpoints (Management & Status Only)
**⚠️ NEVER used for purchasing - use `/api/v1/orders` instead!**

- `GET /api/v1/flash-sales` - List campaigns (for displaying banners)
- `POST /api/v1/flash-sales` - Create campaign (admin only)
- `GET /api/v1/flash-sales/{id}` - Get campaign status (for "Sold Out" badges)
- `PUT /api/v1/flash-sales/{id}` - Update campaign (admin only)
- `DELETE /api/v1/flash-sales/{id}` - Delete campaign (admin only)

**Note:** These endpoints are for campaign management and status display only. All purchases (regular AND flash sale) go through `/api/v1/orders` endpoint. The backend automatically detects if a SKU belongs to an active campaign.

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

## ⚙️ Business Logic

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

## 🧪 Testing Flash Sale Functionality

**IMPORTANT**: The frontend ALWAYS uses the `/api/v1/orders` endpoint for all purchases. The backend automatically detects if a SKU is part of an active flash sale and applies the appropriate validation (campaign limits, customer limits, time windows).

### Order API (Handles Both Regular and Flash Sale Purchases)

```bash
# Same API for regular purchases AND flash sale purchases
# Backend automatically detects if SKU is in an active flash sale
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "customer_name": "Test Customer",
    "currency": "USD",
    "line_items": [
      {
        "sku_id": "650e8400-e29b-41d4-a716-446655440001",
        "quantity": 2
      }
    ]
  }'

# Backend logic:
# 1. Check if SKU is part of active flash sale campaign
# 2. If YES: Validate campaign limits (total_sale_limit, max_quantity_per_customer, time window)
# 3. If NO: Process as regular order
# 4. Always validate SKU-level inventory
# 5. Create order with proper atomicity
```

### Flash Sale Status API (Read-Only, High Performance)

```bash
# Check campaign status (NOT for purchasing)
# Used by frontend to display "Sold Out", "Active", "Ended" badges
curl http://localhost:8000/api/v1/flash-sales/{flash_sale_id}

# List active campaigns (for displaying flash sale banners)
curl http://localhost:8000/api/v1/flash-sales?status=active
```

### Testing Overselling Protection

```bash
# 1. Create a flash sale campaign with total_sale_limit=100
# 2. Send 1000 concurrent requests to /api/v1/orders with flash sale SKU
# 3. Verify exactly 100 orders created (no more, no less)
# 4. Verify 900 requests receive "campaign limit exceeded" error
# 5. Verify zero inventory inconsistencies across all services
```

## 🎯 Inspired by Saleor

This implementation draws inspiration from Saleor's:
- Domain modeling (Product → ProductVariant maps to SPU → SKU)
- API-first design philosophy
- Database schema patterns with proper indexing
- Service layer architecture
- E-commerce entity relationships
