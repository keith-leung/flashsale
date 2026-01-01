# Flash Sale Benchmark - Development Conventions and Policies

## MANDATORY FOR ALL AGENTS

**⚠️ ALL agents (Claude, Gemini, or any AI) MUST read this file BEFORE taking any action.**

This file contains the SACRED CONVENTIONS that govern this repository. Every action, every change, every decision MUST follow these conventions without exception.

---

## 🔥 SACRED VERIFICATION - The Golden Command

**FIRST ACTION IN EVERY SESSION: Run SACRED VERIFICATION**

```bash
bash SACRED_VERIFICATION.sh
```

This is the **GOLDEN COMMAND** that ensures Variant Y is ready. It:
1. Removes any Variant X conflicts (keeps Variant Y sacred)
2. Ensures all services are running (starts them if needed)
3. Runs health checks (HTTP + database)
4. Runs 29 unit tests
5. Runs quick performance benchmark (5s per service)

**Exit Codes:**
- `0` = SACRED VERIFICATION PASSED ✅
- `1` = SACRED VERIFICATION FAILED ❌ (fix issues and re-run)

**Usage Pattern:**
- Human opens conversation → Run SACRED_VERIFICATION.sh → Get status
- LLM loses context → Run SACRED_VERIFICATION.sh → Understand system state
- After code changes → Run SACRED_VERIFICATION.sh → Verify nothing broke
- Before benchmarks → Run SACRED_VERIFICATION.sh → Ensure ready

**This command is IDEMPOTENT and REPRODUCIBLE across all sessions.**

---

## File Organization Convention

**STRICT RULE: Only README.md is allowed in the root directory.**

**File Structure:**
```
/home/syracuse/orange-315-forever/
├── README.md                    ← ONLY MD file in root directory
├── docker-compose.yml           ← Infrastructure configs
├── nginx/                       ← Service configs
├── python-service/              ← Service code
├── java-service/                ← Service code
├── csharp-service/              ← Service code
└── versions/                    ← ALL documentation resides here
    ├── CONVENTIONS.md           ← THIS FILE - All policies consolidated here!
    ├── 20251125_baseline_performance_testing.md  ← Version history
    ├── 20251129_order_api_compatibility_and_performance.md
    ├── 20251226_dockerized_performance_benchmarks.md
    └── 2025MMDD_description.md  ← Future version files follow this pattern
```

**Rules:**
- ✅ README.md is the ONLY MD file allowed in root
- ✅ ALL policies, schemas, guides are consolidated in THIS file (CONVENTIONS.md)
- ✅ /versions/ contains CONVENTIONS.md and dated version files (YYYYMMDD_*.md)
- ✅ Version files document what was done on that date (history/change logs)
- ❌ NEVER create standalone policy MD files (consolidate into CONVENTIONS.md)
- ❌ NEVER scatter documentation across directories

**Why This Convention:**
- Single source of truth: CONVENTIONS.md for all policies
- Clean structure: version history separate from living reference
- Easy to find: agents always know to read CONVENTIONS.md first
- Prevents duplication and confusion

---

## CRITICAL POLICIES - MUST FOLLOW

### Policy 0: Syracuse University Database Credentials - SACRED AND IMMUTABLE

**ALL variants MUST use Syracuse University credentials FOREVER to honor the alma mater.**

**THESE CREDENTIALS ARE IMMUTABLE AND SACRED:**
```yaml
MYSQL_DATABASE: orange315
MYSQL_USER: syracuse
MYSQL_PASSWORD: Orange_315_Forever!
```

**ABSOLUTE REQUIREMENTS:**
- ✅ ALWAYS use these exact credentials for ALL variants
- ✅ EVERY MariaDB instance uses "orange315" database
- ✅ EVERY connection uses "syracuse" user
- ✅ EVERY password is "Orange_315_Forever!"
- ❌ NEVER use root credentials for application connections
- ❌ NEVER change these credentials for ANY reason
- ❌ NEVER use different credentials for different variants
- ❌ NO EXCEPTIONS - This honors Syracuse University 🍊

**Why These Credentials?**
- Syracuse University is the alma mater
- Orange 315 represents Syracuse (area code 315, color orange)
- These credentials are permanent and unchangeable
- All documentation, configs, and code MUST use these credentials

---

### Policy 1: Variant Y is Sacred - NEVER Break It

**Variant Y must remain functional at ALL times. It serves as the regression test baseline.**

- Variant Y is the baseline implementation that all other variants are compared against
- Making Variant Y non-workable is **STRICTLY FORBIDDEN**
- All changes must be verified to not break Variant Y functionality
- If uncertain, test Variant Y first before making any changes

---

### Policy 2: Middleware Always Running - Sacred Availability

**ALL middleware (MariaDB, Redis, Nginx) and application services MUST be always running.**

**Restart Policy:**
```yaml
restart: always  # For ALL services
```

**Requirements:**
- ✅ MariaDB: restart=always (Database must survive WSL/host reboots)
- ✅ Redis: restart=always (Cache must survive restarts)
- ✅ Nginx: restart=always (Load balancer always available)
- ✅ Python Service: restart=always (Always ready for benchmarks)
- ✅ Java Service: restart=always (Always ready for benchmarks)
- ✅ C# Service: restart=always (Always ready for benchmarks)
- ❌ NEVER use restart=unless-stopped or restart=no
- ❌ NEVER require manual startup

**Rationale:**
- Gemini (or any AI) must be able to reproduce benchmarks without code changes
- Services must survive WSL restarts, system reboots, crashes
- Database must always be available at 172.31.250.88:3307
- Benchmarks must be reproducible at ANY time without intervention
- "Sacred" means ALWAYS available, ALWAYS running

---

### Policy 3: Complete Isolation Between Variants

**Each variant MUST have its own dedicated infrastructure. NO SHARING of middleware between variants.**

- **Dedicated MariaDB per variant** - Each variant gets its own MariaDB instance with its own IP and port
- **Dedicated Redis per variant** - Each variant gets its own Redis instance with its own IP
- **Dedicated Nginx per variant** - Each variant gets its own Nginx load balancer
- **Dedicated application services per variant** - Python, Java, C# services are separate per variant
- **Dedicated network per variant** - Each variant runs in its own isolated network namespace

**Rationale:**
- Ensures fair performance comparison without resource contention
- Prevents one variant from affecting another's performance
- Allows true side-by-side benchmarking
- Eliminates cross-variant dependencies

**Examples:**
- ✅ CORRECT: Variant Y uses 10.88.0.2 MariaDB, Variant X uses 10.89.0.2 MariaDB (separate instances)
- ❌ WRONG: Variant Y and Variant X both connect to the same MariaDB at 10.88.0.2

---

### Policy 4: Mandatory Functionality Verification Before Any Change

**BEFORE any change is committed, it MUST pass the complete functionality benchmark.**

Every change must be verified with this complete test sequence:

#### Step 1: Individual Service Health Benchmarks
**Use wrk for performance testing with OPTIMAL concurrency, NOT just curl!**

Test each service directly (not through nginx) with optimal concurrency:
```bash
wrk -t12 -c100 -d30s --latency http://localhost:8000/health   # Python (optimal: -c100)
wrk -t12 -c200 -d30s --latency http://localhost:8081/health   # Java (optimal: -c200)
wrk -t12 -c600 -d30s --latency http://localhost:8082/health   # C# (optimal: -c600)
```

**Success Criteria:**
- All services return 200 OK
- Throughput: >10,000 req/s per service
- Zero errors
- Python: ~41,000 req/s, Java: ~190,000 req/s, C#: ~439,000 req/s

**Returning "200 OK" with curl is NOT sufficient - you MUST measure performance with wrk at optimal concurrency!**

#### Step 2: Nginx -> All Services Health Benchmark
**Use wrk to test load balancer performance with OPTIMAL concurrency:**

```bash
wrk -t12 -c25 -d30s --latency https://localhost:8443/health   # Round-robin (optimal: -c25)
```

**Success Criteria:**
- All routes return 200 OK
- Throughput: >5,000 req/s (load balancer overhead acceptable)
- Expected: ~10,106 req/s at optimal concurrency
- Zero errors
- Nginx correctly routes to backend services

**NOTE:** Only test round-robin endpoint. Individual service routes (python/health, java/health, csharp/health) are not required for verification.

#### Step 3: Individual Service Order Benchmark
**Use wrk with Lua script to test order creation under load with OPTIMAL concurrency:**

```bash
# First: Ensure test data exists (if not already populated)
# podman exec flash-python python /app/setup_test_data.py 500 5 100000

# Then: Run order benchmarks on each service with optimal concurrency
wrk -t12 -c50 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8000/api/v1/orders  # Python (optimal: -c50)
wrk -t12 -c75 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8081/api/v1/orders  # Java (optimal: -c75)
wrk -t12 -c25 -d30s --latency -s /tmp/order_benchmark.lua http://localhost:8082/api/v1/orders  # C# (optimal: -c25)
```

**Flash Sale Campaign Logic (CRITICAL):**
- If a flash sale campaign exists for the SKU, the order API automatically uses the flash sale path
- If no flash sale campaign exists, the order API uses the standard database path
- **Frontend is AGNOSTIC** - it always calls the same `/api/v1/orders` endpoint
- The backend intelligently routes based on whether a flash sale is active
- **NO FRONTEND CODE CHANGES** needed when flash sale is active/inactive

**Success Criteria:**
- Orders are created successfully
- Inventory is decremented correctly
- Flash sale logic activates when campaign exists
- Performance metrics recorded (RPS, latency)
- Expected: Python: ~694 req/s, Java: ~2,630 req/s, C#: ~2,227 req/s
- Zero errors or <0.1% error rate acceptable

#### Step 4: Nginx -> All Services Order Benchmark
**Use wrk to test order creation through load balancer with OPTIMAL concurrency:**

```bash
wrk -t4 -c50 -d30s --latency -s /tmp/order_benchmark.lua https://localhost:8443/api/v1/orders
```

**Success Criteria:**
- Orders distributed across all services (Python, Java, C#)
- Throughput: ~1,113 req/s (constrained by Python, the slowest service)
- Latency: ~68ms average
- Error rate: <10% acceptable (expected: ~9.2% due to Python backpressure)
- **Critical Understanding:** Nginx round-robin throughput matches slowest service capacity, NOT combined capacity
- Optimal concurrency: `-t4 -c50` (matches Python's capacity, not combined)

---

### Policy 5: Changes Without Verification Are STRICTLY FORBIDDEN

**If you cannot run the full functionality benchmark, you CANNOT make the change.**

- No partial testing - must complete all 4 steps
- No "it should work" assumptions - must verify
- No changes during downtimes - wait until you can test
- Document test results in commit messages

### Policy 6: API Backward Compatibility - Order API is Universal

**CRITICAL ARCHITECTURAL DECISION: The frontend ALWAYS uses `/api/v1/orders` for ALL purchases.**

**Rules:**
- ✅ ALL purchases (regular and flash sale) go through `/api/v1/orders` endpoint
- ✅ Backend automatically detects if SKU is part of active flash sale campaign
- ✅ Backend applies flash sale validation transparently (campaign limits, time windows, customer limits)
- ✅ Frontend NEVER calls flash sale endpoints for purchasing
- ✅ Flash sale endpoints (`/api/v1/flash-sales/*`) are READ-ONLY for status/listing
- ✅ Zero frontend changes required when adding/removing flash sales

**Why This Matters:**
- **Backward Compatibility**: Existing clients work without modification
- **Simplicity**: One order API handles all purchase scenarios
- **Transparency**: Frontend doesn't need to know about flash sale mechanics
- **Flexibility**: Flash sales can be added/removed without frontend deployments

**What This Means for Implementations:**
```
POST /api/v1/orders
{
  "line_items": [{"sku_id": "...", "quantity": 2}]
}

Backend logic:
1. Check if SKU is in active flash sale → Apply flash sale validation
2. If not in flash sale → Process as regular order
3. Always validate SKU-level inventory
4. Create order atomically
```

**NEVER:**
- ❌ Require frontend to call different endpoints for flash sale vs regular purchases
- ❌ Require frontend to detect flash sales
- ❌ Break backward compatibility of `/api/v1/orders`

---

## Network Allocation Policy

### Standard IP Allocation Pattern (All Variants)

**Every variant follows this pattern within its /24 subnet:**

```
.2  = MariaDB (Database)      → Syracuse credentials always
.3  = Redis (Cache)            → Port 6379 internal
.4  = Nginx (Load Balancer)    → Port 443 (or variant-specific)
.5  = Python Service           → Port 8000 (or variant-specific)
.6  = Java Service             → Port 8080 (or variant-specific)
.7  = C# Service               → Port 80 (or variant-specific)
.8+ = Reserved for future services
```

### Preallocated Networks

- **Variant Y (Baseline):** 10.88.0.0/24
- **Variant X (Redis Atomic):** 10.89.0.0/24
- **Variant Z (Reserved):** 10.90.0.0/24
- **Variant W (Reserved):** 10.91.0.0/24

### Variant Y Network Configuration

| Service | Internal IP | Host Port | Container Port |
|---------|-------------|-----------|----------------|
| MariaDB | 10.88.0.2   | 3307      | 3306          |
| Redis   | 10.88.0.3   | (internal)| 6379          |
| Nginx   | 10.88.0.4   | 8443      | 443           |
| Python  | 10.88.0.5   | 8000      | 8000          |
| Java    | 10.88.0.6   | 8081      | 8080          |
| C#      | 10.88.0.7   | 8082      | 80            |

**Database accessible from host (WSL IP):** `172.31.250.88:3307`

**Syracuse credentials work everywhere:**
```bash
mysql -h 172.31.250.88 -P 3307 -usyracuse -pOrange_315_Forever! orange315
```

**Connection strings for services:**
```bash
# Python
DATABASE_URL=mysql+aiomysql://syracuse:Orange_315_Forever!@10.88.0.2:3306/orange315

# Java
SPRING_DATASOURCE_URL=jdbc:mysql://10.88.0.2:3306/orange315?useSSL=false&allowPublicKeyRetrieval=true
SPRING_DATASOURCE_USERNAME=syracuse
SPRING_DATASOURCE_PASSWORD=Orange_315_Forever!

# C#
ConnectionStrings__DefaultConnection=Server=10.88.0.2;Port=3306;Database=orange315;User=syracuse;Password=Orange_315_Forever!;
```

---

## Database Schema - Baseline Requirements

### Core Tables and Syracuse Credentials

**EVERY table uses Syracuse University credentials:**
- Database: `orange315`
- User: `syracuse`
- Password: `Orange_315_Forever!`

### Baseline Schema (MariaDB 10.11)

```sql
-- SPUs (Standard Product Units)
CREATE TABLE spus (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(250) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description LONGTEXT,
  is_active TINYINT(1) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SKUs (Stock Keeping Units)
CREATE TABLE skus (
  id CHAR(36) PRIMARY KEY,
  sku_code VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  spu_id CHAR(36) NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  cost_price DECIMAL(10,2),
  weight DECIMAL(8,3),
  track_inventory TINYINT(1) NOT NULL,
  is_active TINYINT(1) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (spu_id) REFERENCES spus(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Inventory
CREATE TABLE inventory (
  id CHAR(36) PRIMARY KEY,
  sku_id CHAR(36) UNIQUE NOT NULL,
  quantity INT NOT NULL,
  reserved_quantity INT NOT NULL,
  allow_negative_stock TINYINT(1) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (sku_id) REFERENCES skus(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Flash Sale Campaigns
-- CRITICAL BUSINESS LOGIC: Campaigns are SPU-level, NOT SKU-level!
-- Example: Campaign for "iPhone 16" (SPU) with 100K total_sale_limit
--          Customers order "iPhone 16 Black 512GB" or "iPhone 16 Silver 128GB" (SKUs)
--          Campaign tracks total across ALL SKUs under the SPU
--          Individual SKU inventory still enforced
CREATE TABLE flash_sale_campaigns (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(250) NOT NULL,
  description LONGTEXT,
  spu_id CHAR(36) NOT NULL,  -- Links to SPU (Product), NOT SKU (Variant)!
  total_sale_limit INT NOT NULL,  -- Total items across ALL SKUs under this SPU
  sold_quantity INT NOT NULL DEFAULT 0,  -- Incremented when ANY SKU under this SPU is ordered
  max_quantity_per_customer INT NOT NULL,
  start_time DATETIME(6) NOT NULL,
  end_time DATETIME(6) NOT NULL,
  status VARCHAR(255) NOT NULL,  -- 'scheduled', 'active', 'ended', 'cancelled'
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (spu_id) REFERENCES spus(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orders
CREATE TABLE orders (
  id CHAR(36) PRIMARY KEY,
  order_number VARCHAR(50) UNIQUE NOT NULL,
  customer_email VARCHAR(255) NOT NULL,
  customer_name VARCHAR(255),
  subtotal DECIMAL(10,2) NOT NULL,
  tax_amount DECIMAL(10,2) NOT NULL,
  shipping_amount DECIMAL(10,2) NOT NULL,
  total_amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) NOT NULL,
  status VARCHAR(255) NOT NULL,
  notes LONGTEXT,
  flash_sale_campaign_id CHAR(36),  -- Optional: set when order was part of flash sale
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (flash_sale_campaign_id) REFERENCES flash_sale_campaigns(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Order Line Items
CREATE TABLE order_line_items (
  id CHAR(36) PRIMARY KEY,
  order_id CHAR(36) NOT NULL,
  sku_id CHAR(36) NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  total_price DECIMAL(10,2) NOT NULL,
  product_name VARCHAR(255) NOT NULL,
  sku_code VARCHAR(255) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  FOREIGN KEY (sku_id) REFERENCES skus(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Payments
CREATE TABLE payments (
  id CHAR(36) PRIMARY KEY,
  order_id CHAR(36) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) NOT NULL,
  payment_method VARCHAR(50) NOT NULL,
  gateway_transaction_id VARCHAR(255),
  gateway_response LONGTEXT,
  status VARCHAR(255) NOT NULL,
  reference_number VARCHAR(100),
  notes LONGTEXT,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Schema Compatibility Rules

✅ **ALLOWED:**
- Add new NULL-able columns
- Add new tables
- Add new indexes
- Widen column types (e.g., VARCHAR(50) → VARCHAR(100))

❌ **FORBIDDEN:**
- Drop existing tables
- Drop existing columns
- Rename tables or columns
- Add NOT NULL columns without defaults
- Change column types in breaking ways

---

## Variant Y Benchmark Reproducibility

### Complete 4-Step Benchmark Procedure

**Step 0: Environment Preparation**
```bash
cd /home/syracuse/orange-315-forever
podman-compose up -d
sleep 30
podman exec flash-python python /app/setup_test_data.py
```

**Step 1: Individual Service Health Benchmarks**
```bash
wrk -t2 -c10 -d10s http://localhost:8000/health  # Python
wrk -t2 -c10 -d10s http://localhost:8081/health  # Java
wrk -t2 -c10 -d10s http://localhost:8082/health  # C#
```

**Expected:** >10,000 req/s, <10ms latency, 0 errors

**Step 2: Nginx Health Benchmark**
```bash
wrk -t2 -c10 -d10s https://localhost:8443/health
```

**Expected:** >5,000 req/s, 0 errors

**Step 3: Individual Service Order Benchmarks**
```bash
wrk -t4 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8000/api/v1/orders
wrk -t4 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8081/api/v1/orders
wrk -t4 -c100 -d30s -s python-service/wrk_order_script.lua http://localhost:8082/api/v1/orders
```

**Expected Results:**
- Python: ~1,400 req/s
- Java: ~3,400 req/s
- C#: ~4,800 req/s
- Error rate: <1%

**Step 4: Nginx Order Benchmark**
```bash
wrk -t4 -c100 -d30s -s python-service/wrk_order_script.lua https://localhost:8443/api/v1/orders
```

**Expected:** ~2,000 req/s

### Latest Baseline Performance Results (December 31, 2025)

**With Optimal Concurrency Parameters:**

| Service | Health (req/s) | Optimal -c | Orders (req/s) | Optimal -c | Latency (Orders) |
|---------|---------------|-----------|----------------|-----------|-----------------|
| Python  | 41,104        | -c100     | 694            | -c50      | 96.51ms         |
| Java    | 184,392       | -c200     | 2,630          | -c75      | 55.50ms         |
| C#      | 469,733       | -c600     | 2,227          | -c25      | 38.69ms         |
| Nginx   | 10,106        | -c25      | 1,113          | -t4 -c50  | 68.32ms         |

**Key Metrics:**
- All health benchmarks: 30 seconds duration, `-t12` threads
- All order benchmarks (direct): 30 seconds duration, `-t12` threads, `/tmp/order_benchmark.lua`
- Nginx order benchmark: 30 seconds duration, `-t4` threads (lower to match Python capacity)
- Reproducibility: ±10% variance across runs
- Error rates: 0% for direct access, ~9.2% for nginx (Python backpressure)

---

## Forbidden Practices

### ❌ NEVER DO THESE:
1. Share MariaDB between variants
2. Share Redis between variants
3. Share Nginx between variants
4. Make changes without testing Variant Y
5. Commit without running full functionality benchmark
6. Use non-standard IP patterns
7. Skip documentation updates
8. Assume "it should work" without verification
9. Make changes while services are down
10. Batch multiple changes without testing each one
11. Change Syracuse credentials for ANY reason
12. Create MD files outside of /versions/
13. Use restart policies other than "always"

### ✅ ALWAYS DO THESE:
1. Test Variant Y before and after changes
2. Run complete functionality benchmark (all 4 steps)
3. Document IP allocations
4. Use dedicated infrastructure per variant
5. Follow standard IP allocation pattern
6. Record benchmark results
7. Revert immediately if Variant Y breaks
8. Ask for clarification if uncertain
9. Test incrementally (one change at a time)
10. Keep Variant Y as the source of truth
11. **Maintain database schema compatibility**
12. **Use Syracuse credentials everywhere**
13. **Read this file before ANY action**

---

**Syracuse Orange Forever! 🍊**
