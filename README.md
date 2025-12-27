# Flash Sale Microservices Platform

A **complete flash sale e-commerce platform** with identical functionality implemented in **Python, C#, and Java**. Designed for **performance testing and architectural comparison** across different optimization strategies.

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
| **C# (ASP.NET Core)** | **4,912 req/s** | **36.07ms** | 152,900 | 100% | **3.3× faster** |
| **Java (Spring Boot)** | **3,324 req/s** | **47.42ms** | 103,102 | 100% | **2.3× faster** |
| **Python (FastAPI)** | 1,470 req/s | 107.32ms | 45,791 | 99.99% | baseline |

### Nginx Load Balancer Performance

#### Test Command

```bash
wrk -t12 -c100 -d30s -s python-service/wrk_order_script.lua \
  https://localhost:8443/api/v1/orders
```

#### Results (Client → Nginx → Services → Database)

| Metric | Value |
|--------|-------|
| **Throughput** | 2,136 req/s |
| **Latency (avg)** | 65.26ms |
| **Total Requests** | 66,390 |
| **Success Rate** | 88.4% |
| **Load Distribution** | Round-robin (Python, Java, C#) |

**Nginx Overhead Analysis:**
- Adds ~31ms average latency
- Reduces throughput from individual service max to 2,136 req/s
- Lower success rate (88.4%) due to Python being slower in the pool
- Round-robin distributes load evenly across all three services

### Key Findings

1. **C# Performance Leader**
   - 4,912 req/s throughput with 36ms latency
   - 100% success rate under load
   - Most cost-effective for production (2-3 instances for 10K req/s)

2. **Java Balanced Performance**
   - 3,324 req/s with 47ms latency
   - 100% success rate
   - Good middle ground (3-4 instances for 10K req/s)

3. **Python Developer Productivity**
   - 1,470 req/s with 107ms latency
   - 99.99% success rate (excellent reliability)
   - Requires 7-8 instances for 10K req/s

4. **Database I/O Bottleneck**
   - All services perform 4-7 database queries per order
   - Performance gap narrows from 17× (/health) to 3.3× (orders)
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

7. **Nginx Load Balancer Trade-offs**
   - Adds SSL termination and load distribution
   - ~31ms latency overhead
   - Success rate drops when slower services are in the pool
   - Consider dedicated pools per service type in production

8. **Production Capacity Planning**
   - C#: Most cost-effective at 4,912 req/s per instance
   - Java: Good balance at 3,324 req/s per instance
   - Python: Development velocity advantage, 1,470 req/s per instance

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
- C# loses 311× performance from /health (996K) to orders (3.2K)
- Java loses 99× performance from /health (172K) to orders (1.7K)
- Python loses 60× performance from /health (95K) to orders (1.5K)

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

1. **Python (Direct):** ~54k req/s
   ```bash
   bash python-service/benchmark_health.sh http://localhost:8000/health
   ```

2. **Java (Direct):** ~195k req/s
   ```bash
   bash java-service/test_health.sh
   ```

3. **C# (Direct):** ~395k req/s
   ```bash
   bash csharp-service/test_health.sh
   ```

### Phase 4: Order Processing (Direct Access)

Measure application logic + DB performance (bypassing load balancer). This is the baseline "business logic" performance.

1. **Python (Direct):** ~1,460 req/s
   ```bash
   bash python-service/benchmark_orders.sh http://localhost:8000/api/v1/orders
   ```

2. **Java (Direct):** ~3,800 req/s
   ```bash
   cd java-service && bash benchmark_orders.sh http://localhost:8081/api/v1/orders
   ```

3. **C# (Direct):** ~5,700 req/s
   ```bash
   cd csharp-service && bash benchmark_orders.sh http://localhost:8082/api/v1/orders
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

## 💡 Technology Choices

### Why MariaDB with InnoDB?

**Optimized for flash sale performance:**
- **Row-level locking**: Prevents overselling with minimal contention
- **MVCC**: Multiple reads during writes
- **ACID compliance**: Data integrity during inventory updates
- **Proven at scale**: Battle-tested for e-commerce

### Why Redis?

- High-performance caching
- Session storage
- Real-time data access

### Why These Frameworks?

- **Python/FastAPI**: Rapid development, async support, strong typing
- **C#/ASP.NET Core**: Enterprise performance, excellent tooling
- **Java/Spring Boot**: Battle-tested ecosystem, comprehensive features

## 📚 Additional Resources

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Multi-WSL setup guide for testing variants
- **[/versions](versions/)** - Historical benchmark results and iterations
- **Swagger Docs**:
  - Python: http://localhost:8000/docs
  - Java: http://localhost:8081/swagger-ui.html
  - C#: http://localhost:8082/swagger

## 🎯 Inspired by Saleor

This implementation draws inspiration from Saleor's:
- Domain modeling (Product → ProductVariant maps to SPU → SKU)
- API-first design philosophy
- Database schema patterns with proper indexing
- Service layer architecture
- E-commerce entity relationships
