# Flash Sale Microservices Platform

A **complete flash sale e-commerce platform** with identical functionality implemented in **Python, C#, and Java**. Designed as a foundation for building different flash sale performance optimizations and testing various architectural approaches.

## Overview

This project provides **three independent microservices** implementing flash sale functionality:

1. **Python Service** - FastAPI + SQLAlchemy + MySQL + Redis
2. **C# Service** - ASP.NET Core + Entity Framework Core + MySQL + Redis  
3. **Java Service** - Spring Boot + JPA + MySQL + Redis

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

## Service Comparison

| Feature | Python (FastAPI) | C# (ASP.NET Core) | Java (Spring Boot) |
|---------|------------------|-------------------|-------------------|
| **Language** | Python 3.11+ | C# .NET 8 | Java 21+ |
| **Web Framework** | FastAPI | ASP.NET Core | Spring Boot 3.2 |
| **ORM** | SQLAlchemy | Entity Framework Core | Spring Data JPA |
| **Database** | PostgreSQL | PostgreSQL | PostgreSQL |
| **Caching** | Redis | Redis | Redis |
| **Documentation** | OpenAPI/Swagger | Swagger | SpringDoc OpenAPI |
| **Background Tasks** | Celery | Hosted Services | @Scheduled |
| **Object Mapping** | Pydantic | AutoMapper | MapStruct |

## Quick Start

Each service can be run independently:

### Python Service
```bash
cd python-service
poetry install
poetry run uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

### C# Service
```bash
cd csharp-service
dotnet restore
dotnet run
# API: https://localhost:7001/swagger
```

### Java Service
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

**All IDs**: Twitter Snowflake format (64-bit) for distributed generation

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

### Common Infrastructure
- **MySQL 8+**: ACID compliance with InnoDB engine, excellent performance for transactional workloads
- **Redis**: High-performance caching and session storage
- **Twitter Snowflake IDs**: Distributed ID generation for zero conflicts

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