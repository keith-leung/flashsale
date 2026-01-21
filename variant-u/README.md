# Variant U - DeepSeek V3.2 Exp Implementation

## Clean Room Declaration
> "I certify that this architecture was designed based solely on the Business Requirements and the Variant Y Baseline. I have not read, copied, or reverse-engineered the implementation code of Variant X or Variant A."

## Architectural Design: Distributed Token Reserve with Async Persistence

### Core Concept
- **Redis Lua Scripts** for atomic SPU campaign limit + SKU inventory validation
- **Immediate Acknowledgment** after Redis operations (sub-ms response time)
- **Background Workers** with batching for durable database persistence
- **Linear Scalability** through stateless service instances + shared Redis

### Business Logic Implementation

#### 1. Campaign Precondition Setup (Benchmark Optimization)
- **Pre-allocation**: Campaign tokens pre-loaded into Redis before sale starts
- **Warm Caches**: Campaign metadata cached in Redis for fast access
- **SKU Mapping**: SPU→SKU relationships cached to avoid database hits

#### 2. Order Processing Flow
```
1. POST /api/v1/orders
   ↓
2. Lua Script (Atomic):
   - Check campaign.total_sale_limit > 0
   - Check sku.inventory > 0  
   - If both true: DECR campaign.limit, DECR sku.inventory
   - Generate order_id, add to Redis stream
   ↓
3. Immediate HTTP 201 Response with order_id
   ↓
4. Background Worker (Async):
   - Batch process Redis stream every 100ms/1000 records
   - Write to MariaDB (orders, order_line_items, payments)
   - Update campaign.sold_quantity in database
```

#### 3. Data Integrity Guarantees
- **No Overselling**: Redis atomic operations ensure consistency
- **No Data Loss**: Redis persistence + background workers ensure durability
- **Recoverability**: Failed database writes retried from Redis stream

### Performance Optimization Strategies

#### Redis Optimization
- **Lua Scripts**: Single round-trip for multi-operation transactions
- **Pipeline Operations**: Batch Redis commands where possible
- **Connection Pooling**: Reuse Redis connections across requests
- **Memory Optimization**: Use Redis hashes for campaign/SKU data

#### Database Optimization  
- **Batch Writes**: Group 1000+ orders per database transaction
- **Connection Pooling**: Maintain warm database connections
- **Write Optimization**: Minimal indexes on write-heavy tables
- **Async Processing**: Non-blocking database operations

#### Service Optimization
- **Stateless Design**: Horizontal scaling with load balancer
- **Connection Reuse**: HTTP/1.1 keep-alive, HTTP/2 where supported
- **Minimal Logging**: Disable debug logs in hot path
- **Memory Pooling**: Reuse objects to reduce GC pressure

### Expected Performance Characteristics

#### Python Implementation Target
- **Health Endpoint**: Match Variant Y's ~27,788 req/s (environment verification)
- **Order Processing**: Target 15,000+ req/s (5x Variant Y Python)
- **Latency**: <5ms for Redis operations + response

#### Java Implementation Target  
- **Health Endpoint**: Match Variant Y's ~188,205 req/s
- **Order Processing**: Target 50,000+ req/s
- **Latency**: <2ms for Redis operations + response

#### C# Implementation Target
- **Health Endpoint**: Match Variant Y's ~358,676 req/s
- **Order Processing**: Target 100,000+ req/s (beat Variant A record)
- **Latency**: <1ms for Redis operations + response

### Implementation Plan

#### Phase 1: Python Implementation
1. Docker environment with dedicated network (10.91.0.0/24)
2. Basic health endpoint matching SACRED performance
3. Redis Lua script for atomic validation
4. Background worker for database persistence
5. Verification script aligned with SACRED format

#### Phase 2: Java Implementation
1. Same architectural patterns as Python
2. Optimize for JVM performance characteristics
3. Connection pooling and thread optimization

#### Phase 3: C# Implementation
1. Same architectural patterns
2. Async/await optimization
3. Memory and connection pooling

### Business Requirement Confirmations (Confirmed)

1. **✅ Campaign Pre-allocation**: Pre-loading campaign tokens into Redis before sale starts is ACCEPTED
2. **✅ Async Persistence**: Immediate Redis response + async database write is ACCEPTED (eventual consistency)
3. **✅ Manual Reconciliation**: Post-sale database reconciliation if workers fall behind is ACCEPTED
4. **✅ Redis Persistence**: Redis with AOF persistence is SUFFICIENT for data durability
5. **✅ Error Handling**: Fail fast on Redis/database errors - benchmark ends on business process failure
6. **✅ Audit Requirement**: If system goes down, audit records must exist for business operators to manually process orders/refunds for customer reputation

### Resource Allocation (Following Pattern)

| Service | Internal IP | Host Port | Container Name |
|---------|-------------|-----------|----------------|
| MariaDB | 10.91.0.2   | 3314      | flash-mariadb-u |
| Redis   | 10.91.0.3   | (internal)| flash-redis-u   |
| Nginx   | 10.91.0.4   | 8447      | flash-nginx-u   |
| Python  | 10.91.0.5   | 30015     | flash-python-u  |
| Java    | 10.91.0.6   | 8018      | flash-java-u    |
| C#      | 10.91.0.7   | 30016     | flash-csharp-u  |

### Success Criteria
1. Python health endpoint matches SACRED baseline performance
2. Order processing exceeds Variant Y Python performance (1,390 req/s)
3. All three language implementations follow same architecture
4. Verification script produces SACRED-compatible CSV output
5. No environmental interference with SACRED VERIFICATION

---

## Design Confirmation and Lock

**✅ Design Confirmed**: All business requirements confirmed. Architecture is now LOCKED.

**Architectural Commitments:**
1. **Redis Lua Scripts** for atomic SPU campaign + SKU inventory validation
2. **Immediate Redis Response** with async database persistence
3. **Eventual Consistency** model with audit trail for manual reconciliation
4. **Linear Scalability** through stateless services + shared Redis
5. **Fail Fast** on business process errors (benchmark ends)

**Implementation Constraints:**
- Design will NOT change due to implementation challenges
- Performance optimizations must stay within this architectural framework
- All three languages (Python, Java, C#) must follow same patterns
- Must produce SACRED-compatible verification output

**Next Step**: Begin Python implementation with health endpoint verification.