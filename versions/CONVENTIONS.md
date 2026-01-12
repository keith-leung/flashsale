# Flash Sale Benchmark - Development Conventions and Policies

## MANDATORY FOR ALL AGENTS

**⚠️ ALL agents (Claude, Gemini, or any AI) MUST read this file BEFORE taking any action.**

This file contains the SACRED CONVENTIONS that govern this repository. Every action, every change, every decision MUST follow these conventions without exception.

---

## 🔥 SACRED VERIFICATION - The Repository-Wide Unit Test

### ⚠️ CRITICAL UNDERSTANDING: SACRED VERIFICATION Tests the Entire Environment

**SACRED VERIFICATION is the unit test for the ENTIRE REPOSITORY, not just Variant Y.**

**What SACRED VERIFICATION Actually Tests:**
- ✅ Tests Variant Y (simplest, most stable implementation)
- ✅ **Validates the ENTIRE environment** (database, network, ports, Docker, resources)
- ✅ Acts as environmental health check for ALL variants

**Critical Understanding:**
```
If you change Variant X and SACRED VERIFICATION fails
    ↓
Your Variant X changes broke the ENVIRONMENT
    ↓
The environment approach is WRONG
    ↓
Fix infrastructure before proceeding
```

**Why Variant Y is the Environment Test:**
- Variant Y is the simplest implementation (pure database transactions)
- If Variant Y can't run → environment is broken
- If Variant Y passes → environment is healthy for all variants
- Variant Y acts as "canary in the coal mine"

**SACRED VERIFICATION validates:**
- ✅ Port allocations and network configuration
- ✅ Database connectivity across all services
- ✅ Docker container orchestration and resource limits
- ✅ Service dependencies and startup order
- ✅ No port conflicts between variants
- ✅ Proper isolation between variant environments

### The Mandatory Workflow for ALL Changes

**BEFORE making changes to ANY variant:**
```bash
# 1. Verify environment is healthy BEFORE changes
bash SACRED_VERIFICATION.sh  # Should PASS

# 2. Make your changes to Variant X (ports, Docker, config, etc.)

# 3. Test if changes broke environment
bash SACRED_VERIFICATION.sh  # CRITICAL TEST
    ↓
    FAILS? → Your changes broke the environment
            → Revert changes and fix environment approach
    ↓
    PASSES? → Environment is still healthy
             → Safe to test Variant X specifically

# 4. Now test variant-specific functionality
bash verify_variant_x.sh
```

**This prevents:**
- ❌ Port conflicts propagating across variants
- ❌ Resource contention breaking other services
- ❌ Network misconfiguration affecting all variants
- ❌ Database connectivity issues going undetected
- ❌ Environmental bugs masquerading as code bugs

### ⚠️ SACRED Schema Alignment (Still Required)

**SACRED is defined by Variant Y. ALL variants MUST align with SACRED schema.**

- ✅ **Variant Y:** Defines the SACRED schema (golden standard, immutable)
- ✅ **Variant X:** MUST use SACRED schema (same tables, same field names, same API)
- ✅ **All Other Variants:** MUST use SACRED schema (implementation differs, schema aligns)

**Key Distinctions:**
- **SACRED VERIFICATION** = Repository-wide environment test (tests Variant Y + environment)
- **Variant X verification** = Variant-specific test (tests X aligns with SACRED)
- **Variant Z verification** = Variant-specific test (tests Z aligns with SACRED)

**Schema Alignment Requirements:**
- All variants use `flash_sale_campaign_id` (not `flash_sale_id`)
- All variants use `flash_sale_campaigns` table (not `flash_sale_events`)
- All variants use the same API endpoint: `/api/v1/orders`
- All variants use Syracuse credentials (orange315 database)

### SACRED VERIFICATION Command (Tests Environment + Variant Y)

**FIRST ACTION IN EVERY SESSION: Run SACRED VERIFICATION**

```bash
bash SACRED_VERIFICATION.sh
```

This is the **REPOSITORY-WIDE UNIT TEST** that validates environmental integrity. It:
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

### Policy 1: Variant Y Defines SACRED - All Variants Must Align

**Variant Y defines the SACRED schema. ALL variants MUST align with this schema.**

**CRITICAL DISTINCTIONS:**
- ✅ **Variant Y:** Defines SACRED (golden baseline, immutable schema)
- ✅ **Variant X:** MUST align with SACRED schema (different implementation, same schema)
- ✅ **Other Variants:** MUST align with SACRED schema (different implementation, same schema)

**Variant Y Requirements:**
- Variant Y must remain functional at ALL times as the regression test baseline
- Variant Y defines the database schema that ALL variants must follow
- Making Variant Y non-workable is **STRICTLY FORBIDDEN**
- All schema changes must be verified to not break Variant Y functionality
- If uncertain about schema, test Variant Y first before making any changes

**All Variants Must:**
- Use the same database schema as Variant Y (same tables, same columns, same field names)
- Use the same API contracts as Variant Y (same endpoints, same request/response formats)
- Use Syracuse credentials (orange315 database)
- Support `/api/v1/orders` endpoint with intelligent routing

**Variants Can Differ In:**
- Implementation approach (Redis atomic counters vs database transactions)
- Performance optimization strategies
- Internal service architecture
- Verification script names (e.g., `verify_variant_x.sh` instead of SACRED_VERIFICATION.sh)

**The ONLY "SACRED VERIFICATION" is for Variant Y.** Other variants have their own named verification scripts.

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

### Policy 3: Complete Isolation Between Variants - NO OVERLAPPING

**Each variant MUST have its own dedicated infrastructure. NO SHARING of middleware between variants.**

**CRITICAL: Environment overlapping among variants WILL BREAK SACRED VERIFICATION.**

**Mandatory Isolation:**
- **Dedicated MariaDB per variant** - Each variant gets its own MariaDB instance with its own IP and port
- **Dedicated Redis per variant** - Each variant gets its own Redis instance with its own IP
- **Dedicated Nginx per variant** - Each variant gets its own Nginx load balancer
- **Dedicated application services per variant** - Python, Java, C# services are separate per variant
- **Dedicated network per variant** - Each variant runs in its own isolated network namespace
- **NO port conflicts** - Each variant uses different host ports
- **NO resource contention** - Variants do not compete for CPU/memory/disk

**Why NO OVERLAPPING is Critical for SACRED VERIFICATION:**
```
SCENARIO: Variant X shares MariaDB with Variant Y
    ↓
Variant X benchmark runs → Heavy database load
    ↓
SACRED VERIFICATION runs → Variant Y tries same database
    ↓
Database connection pool exhausted from Variant X
    ↓
SACRED VERIFICATION FAILS
    ↓
WRONG DIAGNOSIS: "Variant Y is broken"
ACTUAL CAUSE: Environment overlapping (shared database)
```

**Environment overlapping causes:**
- ❌ Port conflicts → Services fail to start
- ❌ Database connection pool exhaustion → SACRED VERIFICATION fails
- ❌ Network namespace collisions → Container startup failures
- ❌ Resource contention → Unpredictable performance degradation
- ❌ False positive failures → SACRED VERIFICATION fails for wrong reasons

**Rationale:**
- Ensures fair performance comparison without resource contention
- Prevents one variant from affecting another's performance
- Allows true side-by-side benchmarking
- Eliminates cross-variant dependencies
- **Keeps SACRED VERIFICATION accurate and reliable**

**Examples:**
- ✅ CORRECT: Variant Y uses 10.88.0.2 MariaDB:3307, Variant X uses 10.89.0.2 MariaDB:3312 (separate instances, separate ports)
- ❌ WRONG: Variant Y and Variant X both connect to the same MariaDB at 10.88.0.2:3307 (WILL BREAK SACRED VERIFICATION)

---

### Policy 4: SACRED VERIFICATION is the Environmental Unit Test

**SACRED VERIFICATION validates the ENTIRE REPOSITORY ENVIRONMENT, not just Variant Y.**

**Critical Rule:**
- When you make changes to ANY variant (X, Z, etc.) and SACRED VERIFICATION fails
- It means your changes broke the ENVIRONMENT (ports, network, Docker, database, resources)
- It does NOT mean Variant Y's code is broken
- The environmental approach is WRONG and must be fixed

**Mandatory Workflow:**
1. Run SACRED VERIFICATION **before** making changes (establishes baseline)
2. Make changes to Variant X (or any variant)
3. Run SACRED VERIFICATION **after** changes (validates environment integrity)
   - ✅ PASSES → Environment is healthy, proceed to variant-specific verification
   - ❌ FAILS → Your changes broke the environment, revert and fix infrastructure
4. Run variant-specific verification (e.g., `verify_variant_x.sh`)

**Why This Matters:**
- Variant Y is the simplest implementation (pure database transactions)
- If the simplest implementation can't run, the environment is misconfigured
- Catching environmental issues early prevents them from propagating across all variants
- Separates environmental problems from code problems

**Examples of Environmental Issues SACRED VERIFICATION Detects:**
- Port conflicts between variants
- Network isolation failures
- Database connection pool exhaustion
- Docker resource limits too low
- Service startup dependency issues
- CPU/memory contention between variants

### Policy 5: Mandatory Functionality Verification Before Any Change

**BEFORE any change is committed, it MUST pass the complete functionality benchmark.**

**CRITICAL REQUIREMENT: All variant test procedures MUST align with SACRED VERIFICATION format.**

**Why This Matters:**
- SACRED VERIFICATION defines the standard test procedure and raw data format
- All variants must follow the SAME test steps, parameters, and data format
- This enables direct performance comparison across variants
- Raw CSV data must be comparable (same columns, same metrics, same test conditions)
- Without alignment, performance comparisons are meaningless

**What "Align with SACRED VERIFICATION" Means:**
1. **Same test sequence:** All variants use the same 4-step procedure as SACRED VERIFICATION
2. **Same test parameters:** Same concurrency levels, duration, endpoints
3. **Same data format:** Raw results must match SACRED VERIFICATION's CSV schema
4. **Same success criteria:** Same performance thresholds and error rate limits
5. **Same measurement approach:** wrk with same flags, same Lua scripts

**Example - Why Alignment is Required:**
```
❌ WRONG: Variant X tests health with -c50, Variant Y with -c100
         → Cannot compare performance (different load conditions)

✅ CORRECT: Both variants test health with -c100 at same duration
           → Performance comparison is valid and meaningful
```

Every change must be verified with this complete test sequence (aligned with SACRED VERIFICATION):

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

#### SACRED VERIFICATION Raw Data Format

**All variant verifications MUST produce data in the same format as SACRED VERIFICATION.**

**Standard CSV Schema:**
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,
duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,
p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,
total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,
socket_errors_read,socket_errors_write,socket_errors_timeout,
transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
```

**Why This Format is Mandatory:**
1. **Cross-variant comparison:** Same columns enable direct performance comparison
2. **Automated analysis:** Tools can process all variant data uniformly
3. **Regression detection:** Compare new results against SACRED baseline
4. **Performance trending:** Track improvements/degradations over time
5. **Standardized reporting:** Generate consistent reports across all variants

**Example - Performance Comparison Enabled by Format Alignment:**
```bash
# Compare order creation performance across variants
grep ",order," benchmark_results/variant_Y_raw_*.csv | awk -F',' '{print $3, $9}'
grep ",order," benchmark_results/variant_X_raw_*.csv | awk -F',' '{print $3, $9}'

# Output (comparable because same format):
# Variant Y: python 536 req/s, java 800 req/s, csharp 1631 req/s
# Variant X: python 2400 req/s, java 3100 req/s, csharp 4200 req/s
#            ↑ 4.5x faster    ↑ 3.9x faster    ↑ 2.6x faster
```

**If variant tests don't align with SACRED format:**
- ❌ Cannot compare performance metrics
- ❌ Cannot validate performance improvements
- ❌ Cannot use standard analysis tools
- ❌ Cannot prove variant X is better than variant Y

---

### Policy 6: Changes Without Verification Are STRICTLY FORBIDDEN

**If you cannot run the full functionality benchmark, you CANNOT make the change.**

- No partial testing - must complete all 4 steps
- No "it should work" assumptions - must verify
- No changes during downtimes - wait until you can test
- Document test results in commit messages

### Policy 7: API Backward Compatibility - Order API is Universal

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

### Policy 8: Clean Room Protocol - Intellectual Property Protection

**To ensure fair benchmarking, new variants must be implemented in a "Clean Room" environment.**

**The Constraint:**
New variants (e.g., B, C, D) are designed to test **original** architectural ideas. Reading the implementation code of existing optimized variants (X and A) contaminates the experiment by leaking their specific optimizations (Atomic Redis DECR, Batching, Partitioning).

**The Declaration:**
Every new variant's `README.md` MUST contain the following "Clean Room Declaration":

> "I certify that this architecture was designed based solely on the Business Requirements and the Variant Y Baseline. I have not read, copied, or reverse-engineered the implementation code of Variant X or Variant A."

**Enforcement:**
- Directories `/variant-x/` and `/variant-a/` contain "Poison Files" (`⚠️_RESTRICTED_ACCESS_VIOLATION.md`).
- Accessing these files triggers an automatic protocol violation for AI agents.
- Agents found accessing these directories will have their variant disqualified.

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
1. **Make changes to ANY variant without running SACRED VERIFICATION first**
2. **Skip SACRED VERIFICATION after making changes** (must validate environment)
3. **Test variants with different parameters than SACRED VERIFICATION** (breaks comparability)
4. **Use different CSV format than SACRED VERIFICATION** (breaks analysis tools)
5. **Create environment overlapping between variants** (WILL BREAK SACRED VERIFICATION)
6. Share MariaDB between variants (environment overlapping)
7. Share Redis between variants (environment overlapping)
8. Share Nginx between variants (environment overlapping)
9. Use same ports for different variants (environment overlapping)
10. Make changes without testing Variant Y
11. Commit without running full functionality benchmark
12. Use non-standard IP patterns
13. Skip documentation updates
14. Assume "it should work" without verification
15. Make changes while services are down
16. Batch multiple changes without testing each one
17. Change Syracuse credentials for ANY reason
18. Create MD files outside of /versions/
19. Use restart policies other than "always"
20. **Assume SACRED VERIFICATION only tests Variant Y** (it tests the ENTIRE environment)
21. **Claim performance improvements without SACRED-aligned data** (unprovable)

### ✅ ALWAYS DO THESE:
1. **Run SACRED VERIFICATION before making any changes** (establishes environment baseline)
2. **Run SACRED VERIFICATION after making changes** (validates environment integrity)
3. **Align all variant test procedures with SACRED VERIFICATION format** (enables performance comparison)
4. Test Variant Y before and after changes
5. Run complete functionality benchmark (all 4 steps matching SACRED)
6. Document IP allocations
7. Use dedicated infrastructure per variant
8. Follow standard IP allocation pattern
9. Record benchmark results in SACRED-compatible CSV format
10. Revert immediately if SACRED VERIFICATION fails (environment is broken)
11. Ask for clarification if uncertain
12. Test incrementally (one change at a time)
13. Keep Variant Y as the source of truth and environment health indicator
14. **Ensure raw data format matches SACRED VERIFICATION schema** (mandatory for comparisons)
15. **Understand SACRED VERIFICATION tests the ENTIRE REPOSITORY ENVIRONMENT**
16. **Maintain database schema compatibility**
17. **Use Syracuse credentials everywhere**
18. **Read this file before ANY action**

---

**Syracuse Orange Forever! 🍊**
