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

## Quick Start

### Prerequisites

Before running the services, ensure you have:
- **MariaDB 10.6.22** (or compatible version) running on `127.0.0.1:3306`
  - Database: `orange315`
  - User: `syracuse`
  - Password: `Orange_315_Forever!`
- **Redis 6.0.16** (or compatible version) running on `127.0.0.1:6380`

### Running Individual Services

Each service can also be run independently:

#### Python Service

**Quick Start with pip:**
```bash
cd python-service
pip install -r requirements.txt
uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

**Or with Poetry:**
```bash
cd python-service
poetry install
poetry run uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

**For detailed setup instructions, see:** [python-service/SETUP.md](python-service/SETUP.md)

#### C# Service
```bash
cd csharp-service
dotnet restore
dotnet run
# API: https://localhost:7001/swagger
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