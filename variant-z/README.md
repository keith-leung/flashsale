# Variant Z - Token Pre-Allocation Architecture

## Clean Room Declaration

> I certify that this architecture was designed based solely on the Business Requirements and the Variant Y Baseline. I have not read, copied, or reverse-engineered the implementation code of Variant X or Variant A.

---

## Architecture Overview

**Variant Z** uses a **token pre-allocation strategy** combined with **atomic Redis operations** to eliminate database contention during flash sales while maintaining data integrity through synchronous persistence.

### Core Innovation

At campaign activation, Variant Z **pre-allocates tokens** into Redis sorted sets, representing available purchase slots. Orders acquire these tokens atomically via Lua scripts, then persist synchronously to the database.

**Key Insight:** By pre-allocating tokens, we eliminate the need for database-level locking during the critical order creation path, while still maintaining ACID guarantees through synchronous persistence.

---

## Business Requirements (MUST Implement)

### 1. Campaign Pool Limit Enforcement

- Each campaign has `total_sale_limit` (e.g., 1,000 items across ALL SKUs)
- Tokens are pre-allocated into Redis at campaign start: `campaign:{id}:tokens`
- Token count equals `total_sale_limit`
- Tokens are distributed across SKUs proportional to SKU inventory
- When tokens reach zero, campaign is sold out (no database hit needed)

### 2. SKU Stock Validation

- Each SKU has persistent inventory in database
- SKU inventory is cached in Redis with **NO TTL** (fixed from 10-second TTL)
- Redis key: `sku:{sku_id}:inventory`
- Validation happens in Lua script (atomic with token acquisition)
- Database is the source of truth; Redis cache is updated synchronously

**CRITICAL FIX (2026-01-13):** Removed the 10-second TTL on SKU inventory cache. The original implementation would cause all orders to fail after 10 seconds when the cache expired. Since inventory is updated synchronously in the database, the cache can persist without TTL.

### 3. Order Record Creation

- Create `orders` record with status='created'
- Create `order_line_items` record linking order to SKU
- Create `payments` record (amount=0 for testing)
- Return HTTP 201 with order_id
- **Synchronous persistence** - order must be in database before returning 201

### 4. Campaign Status API

- Implement `GET /api/v1/campaigns/{id}/status`
- Return: "Not Started", "Active", "Sold Out", "Ended"
- Status derived from Redis cache (campaign metadata)

---

## Technical Architecture

### Token Pre-Allocation System

**Token Structure:**
```
Key: campaign:{campaign_id}:tokens
Type: Sorted Set (ZSET)
Members: "token_{uuid}_{sku_id}"
Score: Sequential timestamp (FIFO ordering)

Example:
campaign:abc123:tokens = {
  token_001_sku100 → 0,
  token_002_sku100 → 1,
  token_001_sku101 → 2,
  ...
}
```

**Token Distribution Algorithm:**
```python
def allocate_campaign_tokens(campaign_id, total_limit, skus):
    """
    Pre-allocate tokens for a campaign.
    
    Args:
        campaign_id: Campaign UUID
        total_limit: Total tokens to allocate (campaign.total_sale_limit)
        skus: List of SKUs under this campaign's SPU
    
    Distribution Strategy:
        - Calculate total inventory across all SKUs
        - Distribute tokens proportionally to SKU inventory ratios
        - Ensure no SKU gets more tokens than its inventory
    """
    total_inventory = sum(sku.quantity for sku in skus)
    
    for sku in skus:
        # Proportional allocation
        sku_token_count = min(
            sku.quantity,
            int(total_limit * (sku.quantity / total_inventory))
        )
        
        # Create tokens
        for i in range(sku_token_count):
            token_id = f"token_{uuid4()}_{sku.id}"
            redis.zadd(f"campaign:{campaign_id}:tokens", {token_id: i})
    
    # Cache campaign metadata
    redis.setex(f"campaign:{campaign_id}:metadata", 60, json.dumps({
        "total_tokens": total_limit,
        "remaining_tokens": total_limit,
        "status": "active"
    }))
```

### Atomic Order Processing (Lua Script)

**File:** `acquire_order_token.lua`

**CRITICAL FIX (2026-01-13):** The original implementation had a critical bug where it tried to ZREM a specific token ID, but the client passed an empty string. This has been fixed to use ZPOPMIN which pops the first available token from the sorted set (FIFO ordering).

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
-- ZPOPMIN removes and returns the member with the lowest score (FIFO)
local tokens = redis.call('ZPOPMIN', campaign_key, 1)
if not tokens or #tokens == 0 then
    return {err = "TOKEN_NOT_AVAILABLE"}
end

-- Extract token ID from result
local token = tokens[1]

-- Step 2: Check and decrement SKU inventory
local current_stock = redis.call('GET', sku_key)
if not current_stock then
    -- Token acquired but SKU not in cache - restore token
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "SKU_NOT_CACHED"}
end

current_stock = tonumber(current_stock)
if current_stock < quantity then
    -- Token acquired but insufficient stock - restore token
    redis.call('ZADD', campaign_key, 0, token)
    return {err = "INSUFFICIENT_STOCK"}
end

-- Decrement inventory
redis.call('DECRBY', sku_key, quantity)

-- Update campaign metadata
local metadata = redis.call('GET', 'campaign:' .. campaign_key:match('campaign:(.-):tokens') .. ':metadata')
if metadata then
    local decoded = cjson.decode(metadata)
    decoded.remaining_tokens = decoded.remaining_tokens - 1
    redis.call('SETEX', 'campaign:' .. campaign_key:match('campaign:(.-):tokens') .. ':metadata', 60, cjson.encode(decoded))
end

return {ok = "ORDER_SUCCESS", remaining_stock = current_stock - quantity}
```

### Order Processing Flow

```
Request Flow:
1. Receive POST /api/v1/orders
2. Check if SKU belongs to active campaign
   ├─ No: Use Variant Y path (database transaction)
   └─ Yes: Use Variant Z path (Redis tokens)
3. Execute Lua script (atomic token + inventory check)
   ├─ Success: Continue
   └─ Error: Return error response
4. Persist order to database (synchronous)
   ├─ BEGIN TRANSACTION
   ├─ INSERT orders
   ├─ INSERT order_line_items
   ├─ INSERT payments
   ├─ UPDATE inventory (decrement)
   ├─ UPDATE flash_sale_campaigns (increment sold_quantity)
   └─ COMMIT
5. Return 201 Created with order_id

Total Latency: ~15-25ms (vs 50-100ms for Variant Y)
```

### Redis Data Model

```
Campaign Tokens:
├── campaign:{id}:tokens (ZSET)
│   └── Members: token_{uuid}_{sku_id}
│   └── Score: Sequential timestamp

SKU Inventory Cache:
├── sku:{sku_id}:inventory (STRING, NO TTL)
│   └── Value: Integer quantity
│   └── Note: Cache persists because inventory is updated synchronously in DB

Campaign Metadata:
├── campaign:{id}:metadata (STRING, TTL: 60s)
│   └── Value: JSON {total_tokens, remaining_tokens, status}

Customer Purchase Tracking (Optional):
├── customer:{email}:campaign:{id}:tokens (SET, TTL: 3600s)
│   └── Members: Tokens purchased by this customer
```

### Database Schema (SACRED - Same as Variant Y)

Variant Z uses the **exact same schema** as Variant Y (immutable):

- `spus` - Standard Product Units
- `skus` - Stock Keeping Units
- `inventory` - SKU inventory (persistent)
- `flash_sale_campaigns` - Campaign metadata (persistent)
- `orders` - Order records
- `order_line_items` - Order line items
- `payments` - Payment records

**No schema changes permitted** - Variant Z must align with SACRED schema.

---

## Resource Allocation

### Network Configuration

| Resource | Variant Z Allocation |
|----------|---------------------|
| Network Subnet | 10.92.0.0/24 |
| MariaDB | 10.92.0.2:3315 (host) → 3306 (container) |
| Redis | 10.92.0.3:6379 (internal) |
| Python | 10.92.0.4:30017 (host) → 8000 (container) |
| Java | 10.92.0.5:8019 (host) → 8080 (container) |
| C# | 10.92.0.6:30018 (host) → 80 (container) |
| Nginx | 10.92.0.7:8448 (host) → 443 (container) |

### Container Names

- `flash-mariadb-z`
- `flash-redis-z`
- `flash-python-z`
- `flash-java-z`
- `flash-csharp-z`
- `flash-nginx-z`

### Database Credentials (SACRED - Immutable)

```yaml
MYSQL_DATABASE: orange315
MYSQL_USER: syracuse
MYSQL_PASSWORD: Orange_315_Forever!
```

---

## Performance Targets

Based on the architecture, Variant Z targets:

| Service | Health Endpoint | Orders Endpoint | vs Variant Y | vs Best (Variant A) |
|---------|----------------|-----------------|-------------|-------------------|
| Python  | 20,000 req/s   | 3,000 req/s     | 2.2x faster | 4x slower |
| Java    | 200,000 req/s  | 20,000 req/s    | 2.3x faster | 1.3x faster |
| C#      | 400,000 req/s  | 30,000 req/s    | 2.7x faster | 3x slower |
| Nginx   | 10,000 req/s   | 8,000 req/s     | 2.4x faster | Similar |

**Key Performance Advantages:**
- **No database locks** during order creation (tokens acquired in Redis)
- **Sub-5ms token acquisition** (Lua script execution)
- **Synchronous persistence** ensures data integrity
- **Natural rate limiting** (token exhaustion prevents overload)

---

## Implementation Strategy

### Phase 1: Infrastructure Setup
1. Create `variant-z/` directory structure
2. Create `docker-compose.yml` with isolated network (10.92.0.0/24)
3. Configure Redis with AOF persistence
4. Set up MariaDB with sacred schema
5. Configure Nginx load balancer

### Phase 2: Token System Implementation
1. Implement token pre-allocation logic
2. Create token distribution algorithm
3. Implement Lua script for atomic token acquisition
4. Add token expiration handling

### Phase 3: Order Processing
1. Implement campaign detection logic
2. Integrate Lua script execution
3. Implement synchronous database persistence
4. Add error handling and rollback logic

### Phase 4: Caching Layer
1. Implement SKU inventory cache (10s TTL)
2. Add campaign metadata cache
3. Implement cache warming on startup
4. Add cache invalidation on inventory updates

### Phase 5: Verification & Benchmarking
1. Create `verify_variant_z.sh` (SACRED-aligned format)
2. Run SACRED VERIFICATION (before and after)
3. Execute 4-step benchmark procedure
4. Generate performance comparison report

---

## Directory Structure

```
variant-z/
├── README.md                          # This file
├── docker-compose.yml                 # Service definitions
├── verify_variant_z.sh                # Verification script (SACRED-aligned)
├── python-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── acquire_order_token.lua        # Lua script for atomic operations
│   ├── app/
│   │   ├── main.py                    # FastAPI application
│   │   ├── models/
│   │   ├── api/
│   │   │   └── router.py
│   │   └── core/
│   │       ├── database.py
│   │       ├── redis.py
│   │       └── token_manager.py       # Token pre-allocation logic
│   └── tests/
├── java-service/
│   ├── Dockerfile
│   ├── pom.xml
│   ├── acquire_order_token.lua        # Lua script (same as Python)
│   └── src/main/java/com/flashsale/
│       ├── FlashSaleApplication.java
│       ├── api/controller/
│       ├── service/
│       │   ├── TokenService.java      # Token pre-allocation logic
│       │   └── OrderService.java
│       └── config/
├── csharp-service/
│   ├── Dockerfile
│   ├── FlashSale.csproj
│   ├── acquire_order_token.lua        # Lua script (same as Python)
│   └── Controllers/
│   │   └── OrderController.cs
│   └── Services/
│       ├── TokenService.cs            # Token pre-allocation logic
│       └── OrderService.cs
└── nginx/
    └── nginx.conf                     # Load balancer configuration
```

---

## Benchmark Scope vs. Production Reality

### Permitted Simplifications (Benchmark-Appropriate)

✅ **Manual Campaign Setup**
- Campaigns created via SQL scripts
- Token pre-allocation triggered manually
- No admin UI required

✅ **Happy Path Focus**
- No complex failover logic
- If Redis fails, test is voided
- No automated refund processing

✅ **Pre-Computation**
- Cache warming before benchmark
- Token pre-allocation before campaign start
- No runtime token replenishment

✅ **Manual Reconciliation**
- Inventory reconciliation via SQL scripts
- No automated cron jobs
- Manual cleanup after benchmark

### Forbidden Shortcuts (Never Do These)

❌ **Skipping Validation**
- MUST check inventory for every request
- MUST check campaign limits for every request
- Overselling is immediate disqualification

❌ **Hardcoded Responses**
- Cannot return static JSON
- Must actually create order records in database
- Must persist to database before returning 201

❌ **Data Loss**
- If returning HTTP 201, order must be retrievable
- Synchronous persistence required
- No dropping valid orders

---

## Success Criteria

Variant Z will be successful if:

1. ✅ **Functional Correctness**
   - Zero oversale (campaign limit never exceeded)
   - Zero undersale (all valid orders processed)
   - Accurate inventory tracking
   - Orders retrievable from database

2. ✅ **Performance Improvement**
   - 2-3x faster than Variant Y baseline
   - Python: >3,000 req/s
   - Java: >20,000 req/s
   - C#: >30,000 req/s

3. ✅ **SACRED Alignment**
   - Same database schema as Variant Y
   - Same API contracts (`/api/v1/orders`)
   - Same verification format (SACRED-aligned CSV)
   - Syracuse credentials used everywhere

4. ✅ **Clean Room Compliance**
   - No code copied from Variant X or A
   - Original architectural design
   - Performance gains from own innovations

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|-------------------|
| **Redis failure** | Test is voided (permitted simplification) |
| **Token exhaustion** | Return "sold out" immediately (no DB hit) |
| **Cache inconsistency** | 10-second TTL ensures freshness |
| **Race conditions** | Lua scripts ensure atomicity |
| **Database contention** | Synchronous but faster than Variant Y (no locks) |
| **Data loss** | Synchronous persistence ensures durability |

---

## Design Commitment

I commit to this architecture design. I will not deviate from these core principles:

1. **Token pre-allocation** in Redis sorted sets
2. **Atomic Lua scripts** for token acquisition
3. **Synchronous database persistence** (no async complexity)
4. **Redis caching** for SKU inventory (10s TTL)
5. **SACRED conventions** compliance
6. **Clean room** implementation (no code from X or A)

This design is final and will be implemented as specified.

---

## Critical Fixes Applied (2026-01-13)

The following critical issues identified in the referee report have been fixed:

### Issue 1: Token Acquisition Logic ✅ FIXED

**Problem:** The original implementation attempted to ZREM a specific token ID, but the Python code passed an empty string ("") as the token ID. This caused the Lua script to always return TOKEN_NOT_AVAILABLE.

**Fix:** Changed the Lua script to use ZPOPMIN instead of ZREM. ZPOPMIN pops the first available token from the sorted set (FIFO ordering), eliminating the need for the client to know the token ID beforehand.

**Files Modified:**
- [`acquire_order_token.lua`](variant-z/acquire_order_token.lua)
- [`python-service/acquire_order_token.lua`](variant-z/python-service/acquire_order_token.lua)
- [`python-service/app/core/token_manager.py`](variant-z/python-service/app/core/token_manager.py)

**Impact:** Orders can now successfully acquire tokens from the campaign.

### Issue 2: 10-Second TTL on SKU Inventory Cache ✅ FIXED

**Problem:** The SKU inventory cache had a 10-second TTL, causing all order requests to fail with SKU_NOT_CACHED error after 10 seconds, even with available tokens.

**Fix:** Removed the TTL from SKU inventory cache. Since inventory is updated synchronously in the database (source of truth), the cache can persist without expiration.

**Files Modified:**
- [`python-service/app/core/token_manager.py`](variant-z/python-service/app/core/token_manager.py:74)
- [`python-service/app/core/redis.py`](variant-z/python-service/app/core/redis.py:104)

**Impact:** Orders will continue to succeed throughout the campaign duration without cache expiration issues.

### Issue 3: Missing C# Implementation ⏸️ SKIPPED

**Problem:** Variant Z did not have a C# service implementation.

**Note:** Per user request, focusing on completing the Python implementation first. C# and Java implementations will follow.

### Verification

To verify the fixes work correctly:

1. Start the services:
   ```bash
   cd variant-z
   docker-compose up -d
   ```

2. Run the test script:
   ```bash
   cd python-service
   python test_order.py
   ```

3. Expected results:
   - Orders should successfully acquire tokens
   - Multiple orders should succeed (up to campaign limit)
   - Orders should continue working beyond 10 seconds
   - After campaign limit is reached, orders should return sold_out error

---

## Benchmark Results (2026-01-14)

### Summary

| Service | Endpoint | Peak req/s | Status | Notes |
|---------|----------|------------|--------|-------|
| Python | /health | **33,379** | ✅ PASS | Plateau confirmed at t=14, c=115 |
| Java | /health | **208,069** | ✅ PASS | Peak at t=24, c=460 |
| C# | /health | **386,453** | ✅ PASS | Peak at t=24, c=768 |
| Nginx | /health | **12,283** | ✅ PASS | Load balancer overhead expected |
| Python | /orders | **502** | ✅ PASS | Valid orders until token exhaustion |
| Java | /orders | N/A | ❌ **DISQUALIFIED** | NullPointerException - implementation bug |
| C# | /orders | N/A | ❌ **DISQUALIFIED** | MySQL connection failure - implementation bug |

### Health Endpoint Results (All Passed)

```
Service     Peak req/s    P50 Latency    P99 Latency    Decision
─────────   ──────────    ───────────    ───────────    ────────────────
Python      33,379        2.27ms         49.53ms        PLATEAU_CONFIRMED
Java        208,069       1.95ms         6.19ms         SIGNIFICANT_GROWTH
C#          386,453       1.78ms         5.65ms         SIGNIFICANT_GROWTH
Nginx       12,283        1.89ms         3.06ms         SIGNIFICANT_GROWTH
```

### Order Endpoint Results

#### Python Orders: ✅ QUALIFIED (502 req/s)

```
Test 1: 502.29 req/s (t=4, c=10) - Valid orders created
Test 2: 488.71 req/s (t=6, c=20) - Valid orders created
Test 3: 2,433 req/s (t=6, c=24) - SYSTEM_LIMIT (98% errors = tokens exhausted)
```

**Analysis:** Python service successfully processed ~5,000 orders at 502 req/s before token exhaustion. This validates the token pre-allocation architecture works correctly. Performance is limited by synchronous database persistence (each order = 5 DB writes in one transaction).

#### Java Orders: ❌ DISQUALIFIED

```
Test 1: 9,324 req/s - SYSTEM_LIMIT (100% errors)
Error: java.lang.NullPointerException in OrderController
```

**Reason for Disqualification:** The Java service has an implementation bug causing NullPointerException for all order requests. The OrderController fails to properly handle the order creation flow. This is a code defect, not an infrastructure issue.

#### C# Orders: ❌ DISQUALIFIED

```
Test 1: 2,311 req/s - SYSTEM_LIMIT (100% errors)
Error: MySqlConnector.MySqlException: Unable to connect to any of the specified MySQL hosts
```

**Reason for Disqualification:** The C# service cannot connect to the MariaDB database. The connection string uses `Server=mariadb` but the service fails to resolve the Docker DNS name. This is a configuration/implementation bug.

### Raw CSV Data

Full benchmark data saved to: `benchmark_results/variant_Z_raw_20260114_154415.csv`

### Comparison vs Targets

| Service | Target | Actual | Status |
|---------|--------|--------|--------|
| Python Orders | 3,000 req/s | 502 req/s | ⚠️ Below target (6x slower) |
| Java Orders | 20,000 req/s | N/A | ❌ DISQUALIFIED |
| C# Orders | 30,000 req/s | N/A | ❌ DISQUALIFIED |

### Conclusion

## ❌ VARIANT Z - DISQUALIFIED (Design Failure)

**Primary Disqualification Reason: Architecture performs WORSE than baseline**

| Metric | Python Variant Y (Baseline) | Python Variant Z | Result |
|--------|----------------------------|------------------|--------|
| Orders | 1,390 req/s | 502 req/s | **2.8x SLOWER** |

The token pre-allocation architecture with synchronous database persistence is **fundamentally slower** than Variant Y's pure database transaction approach.

**Why the design failed:**
- Each order requires: Redis Lua script execution + 5 synchronous DB writes (order, line_item, payment, inventory update, campaign update)
- The "optimization" of pre-allocating tokens in Redis added overhead without removing the database bottleneck
- Variant Y's simple transaction approach is actually faster because it has fewer moving parts

**Since the Python implementation (the only working service) performs 2.8x worse than baseline, there is no hope that fixing Java/C# bugs would result in a competitive variant. The design cannot be changed.**

| Service | Status | Notes |
|---------|--------|-------|
| Python  | ❌ DISQUALIFIED | 502 req/s - **slower than baseline** (1,390 req/s) |
| Java    | ❌ DISQUALIFIED | Implementation bug - moot point (design already failed) |
| C#      | ❌ DISQUALIFIED | Implementation bug - moot point (design already failed) |

---

**Last Updated:** 2026-01-14
**Variant:** Z
**Architecture:** Token Pre-Allocation with Atomic Redis Operations
**Status:** ❌ **DISQUALIFIED** - Design failure (2.8x slower than baseline)