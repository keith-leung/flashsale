# Flashsale Benchmark Testing Repository

> **For New Agents:** Start here. This README contains everything you need to understand, run, and record benchmark tests.

---

## ⚠️ CRITICAL REQUIREMENT - READ THIS FIRST

**MANDATORY FOR ALL AGENTS (Claude, Gemini, or ANY AI):**

**BEFORE taking ANY action in this repository, you MUST:**

1. **READ** `versions/CONVENTIONS.md` in its entirety
2. **UNDERSTAND** all SACRED policies, especially:
   - Policy 0: Syracuse University credentials (immutable)
   - Policy 1: Variant Y defines SACRED schema (all variants align)
   - Policy 4: SACRED VERIFICATION is the environmental unit test
   - Policy 7: API backward compatibility (`/api/v1/orders` is universal)
3. **VERIFY** you understand the intelligent routing architecture
4. **CONFIRM** you understand that SACRED VERIFICATION tests the ENTIRE REPOSITORY ENVIRONMENT
5. **KNOW** the mandatory workflow: Change → SACRED VERIFICATION → Variant verification

**Why This Matters:**
- Violating conventions can break the golden baseline (Variant Y)
- Using wrong endpoints invalidates benchmark comparisons
- Skipping verification wastes hours debugging preventable issues

**Proof of Understanding:**
- Can you explain why `/api/v1/flash-sale-campaigns/{id}/orders` is FORBIDDEN?
- Do you know what Syracuse credentials to use for ALL variants?
- Can you describe how backend intelligent routing works?
- **Can you explain why SACRED VERIFICATION must run FIRST when changing ANY variant?**

If you cannot answer these questions, **STOP** and read CONVENTIONS.md now.

---

## ⛔ CRITICAL: Variant Implementation Intellectual Property

**If you are implementing a NEW variant (B, C, D, etc.), you are STRICTLY FORBIDDEN from:**

❌ Reading `/variant-x/` directory and all subdirectories
❌ Reading `/variant-a/` directory and all subdirectories
❌ Reading any other `/variant-*/` directories
❌ Studying implementation code from other variants
❌ Reading architecture documentation from other variants
❌ Copying or adapting solutions from other variants

**You MAY ONLY read:**

✅ This README.md file (root directory)
✅ `versions/CONVENTIONS.md` (schema and API contracts)
✅ Variant Y services (Root-Level): `python-service/`, `java-service/`, `csharp-service/`
✅ Database schema files (e.g., `migrations/001_add_flash_sale_campaigns.sql`)
✅ Performance numbers (no implementation details)

**WHY THIS RESTRICTION EXISTS:**

Each variant represents original architectural research. The purpose of this repository is to compare DIFFERENT approaches to the same problem. If you copy another variant's architecture, you defeat the entire purpose of the comparison.

**Your variant's performance gains MUST come from YOUR architectural innovations, not from copying someone else's work.**

If caught violating this restriction, your variant will be rejected.

---

## 🔥 CRITICAL METHODOLOGY - SACRED VERIFICATION IS THE UNIT TEST

**BEFORE making changes to ANY variant, you MUST understand this:**

### SACRED VERIFICATION = Repository-Wide Environmental Unit Test

```
SACRED VERIFICATION is NOT just a Variant Y test.
It is the UNIT TEST for the ENTIRE REPOSITORY ENVIRONMENT.
```

**The Mandatory Workflow:**
```bash
# 1. Before making ANY changes to ANY variant
bash scripts/verification/SACRED_VERIFICATION.sh  # Establishes environment baseline

# 2. Make your changes to Variant X (ports, Docker, resources, code)

# 3. After changes - Test environmental integrity
bash scripts/verification/SACRED_VERIFICATION.sh  # CRITICAL TEST
    ↓
    FAILS? → Your changes BROKE THE ENVIRONMENT
            → Revert and fix infrastructure approach
    ↓
    PASSES? → Environment is still healthy
             → Safe to verify variant-specific functionality

# 4. Now test variant-specific functionality
bash variant-x/verify_variant_x.sh
```

**Why This Methodology:**
- If you change Variant X and SACRED VERIFICATION fails
- It means your Variant X changes broke the ENVIRONMENT (ports, network, Docker, database)
- It does NOT mean Variant Y's code is broken
- The environmental approach is WRONG and must be fixed

**Variant Y is the "canary in the coal mine":**
- Simplest implementation (pure database transactions)
- If Variant Y can't run → environment is misconfigured
- If Variant Y passes → environment is healthy for all variants

**This prevents:**
- Port conflicts propagating across variants
- Resource contention breaking other services
- Network issues affecting all variants
- Environmental bugs masquerading as code bugs

**READ THIS SECTION BEFORE ANY ACTION IN THIS REPOSITORY.**

---

## Table of Contents
1. [Business Requirements & System Logic](#1-business-requirements--system-logic)
2. [API Design](#2-api-design)
3. [The Baseline (Variant Y)](#3-the-baseline-variant-y)
4. [Complete Performance Comparison](#4-complete-performance-comparison---all-variants)
5. [Sacred Conventions & Idempotence](#5-sacred-conventions--idempotence)
6. [Quick Start (5 Minutes)](#6-quick-start-5-minutes)
7. [Repository Structure & Navigation](#7-repository-structure--navigation)
8. [Running Benchmarks](#8-running-benchmarks-step-by-step)
9. [Implementing Your Own Variant](#9-implementing-your-own-variant---guide-for-newcomer-models)
10. [Version History & Notes](#10-version-history--notes)

---

## 1. Business Requirements & System Logic

### Core Business Model
This is a **high-performance e-commerce order processing system** designed to handle **flash sale campaigns** with extreme concurrency.

**Critical Performance Goal:**
> **100,000 ORDER REQUESTS within 1 second, zero 503 errors, no oversale**

### SPU vs SKU Concept

**SPU (Standard Product Unit):**
- Represents a product type (e.g., "iPhone 15 Pro")
- Business managers design flash sale campaigns at **SPU level**
- Campaign has `total_sale_limit` (e.g., 1,000 units of iPhone 15 Pro across ALL variants)
- Campaign has `start_time` and `end_time`

**SKU (Stock Keeping Unit):**
- Specific variant of an SPU (e.g., "iPhone 15 Pro, 256GB, Black")
- Each SKU has **separate persistent stock inventory**
- Multiple SKUs belong to one SPU

**Example:**
```
SPU: "iPhone 15 Pro"
  Campaign: total_sale_limit = 1,000 units (TOTAL across all variants)
  
  SKUs under this SPU:
    - SKU-001: iPhone 15 Pro, 128GB, Black (stock: 300 units)
    - SKU-002: iPhone 15 Pro, 256GB, Black (stock: 400 units)
    - SKU-003: iPhone 15 Pro, 512GB, Silver (stock: 300 units)
```

### Flash Sale Business Rules

**For a purchase to succeed, TWO conditions must BOTH be true:**
1. **SPU-level limit:** Campaign's `total_sale_limit` not exceeded (enforced globally across all SKU variants)
2. **SKU-level stock:** Specific SKU's stock > 0 (enforced per individual SKU)

**Critical Scenario:**
- Campaign: 1,000 items at SPU level
- 100,000 purchase attempts in first second
- System must:
  - ✅ Process all 100,000 requests without 503 errors
  - ✅ Only allow first 1,000 valid orders to complete
  - ✅ Prevent oversale (999 or 1,001 orders = FAILURE)
  - ✅ Maintain consistency across distributed load-balanced servers

### Data Integrity Requirements

**Absolute consistency:**
- SPU campaign limit tracking must be perfectly accurate across all servers
- SKU stock must be perfectly accurate across all servers
- No race conditions, no oversale, no undersale

**High availability:**
- System must handle 100,000 concurrent requests
- Distributed environment (multiple load-balanced servers)
- Read-heavy workload for sale status API
- Write-heavy workload for order creation

### Services Architecture
- **Python (FastAPI):** Async I/O, lightweight for simple endpoints
- **Java (Spring Boot):** Enterprise-grade, excellent connection pooling
- **C# (ASP.NET Core):** High-performance async, superior database handling
- **Nginx:** HTTPS load balancer, round-robin distribution across backends
- **MariaDB:** Relational database for products, SKUs, orders
- **Redis:** Used by Variants X and A for caching/concurrency (Optional for new variants)

### Performance Strategy: Efficiency First, Then Scale

**The Philosophy:**
1.  **Single-Service Efficiency:** Your primary goal is to optimize the *efficiency* of a single service instance.
    *   **The Ceiling:** Your order processing throughput cannot exceed your `/health` endpoint throughput (theoretical framework limit).
    *   **The Goal:** Minimize the gap between `/orders` and `/health`. If `/health` is 20k req/s, achieving 12k req/s for orders is excellent efficiency (60%).
2.  **Horizontal Scalability:** The 100,000 req/s target is an **Aggregate Goal**.
    *   It is acceptable if a single instance "only" handles 15,000 req/s, provided it scales linearly.
    *   Deploying 7-8 such instances behind Nginx to hit 100k req/s is a valid and successful architecture.
    *   **However:** Variants like C# Variant A have proven that getting close to 100k on a *single* instance is possible!

---

## 2. API Design

### Order Creation API (Generic, Backward-Compatible)

**Endpoint:** `POST /api/v1/orders`

**Handles BOTH:**
- Regular orders (normal inventory check)
- Flash sale orders (campaign limit + SKU stock check)

**Request:**
```json
POST /api/v1/orders
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "line_items": [
    {
      "sku_id": "650e8400-e29b-41d4-a716-446655440001",
      "quantity": 2
    }
  ],
  "currency": "USD"
}
```

**Response (Success):**
```json
{
  "order_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "status": "created",
  "total_amount": 0.0,
  "customer_email": "john@example.com"
}
```

**Response (Flash Sale Sold Out):**
```json
{
  "error": "Flash sale sold out",
  "campaign_id": "abc-123",
  "sold_out_at": "2026-01-02T10:00:01Z"
}
```

### Sale Status API (High-Read Performance)

**Endpoint:** `GET /api/v1/campaigns/{campaign_id}/status`

**Returns real-time sale state:**
```json
{
  "campaign_id": "abc-123",
  "spu_id": "def-456",
  "status": "Active",
  "total_sale_limit": 1000,
  "remaining": 247,
  "start_time": "2026-01-02T10:00:00Z",
  "end_time": "2026-01-02T11:00:00Z"
}
```

**Possible status values:** `"Not Started"` | `"Active"` | `"Sold Out"` | `"Ended"`

**Design principle:** This API handles MUCH higher read load than order creation without impacting transaction performance.

**Critical Note:** There is NO `/api/v1/flash-sale-orders` endpoint. The standard `/api/v1/orders` API automatically handles flash sale logic when SKU belongs to an active campaign.

---

## 3. The Baseline (Variant Y)

**Definition:**
Variant Y is the "Sacred Baseline". It represents the standard, robust, database-transaction-based implementation. It prioritizes correctness over raw speed.

**Location:**
Variant Y services reside in the **Root Directories**:
- Python: `/home/syracuse/flashsale/python-service/`
- Java: `/home/syracuse/flashsale/java-service/`
- C#: `/home/syracuse/flashsale/csharp-service/`

**Schema Source of Truth:**
The database schema defined by Variant Y is the immutable standard for all variants.
- **Authoritative SQL:** `migrations/001_add_flash_sale_campaigns.sql`

**Implementation Details (Variant Y Only):**
- **Inventory Check:** `SELECT ... FOR UPDATE` (Pessimistic Locking) in MariaDB.
- **Limit Check:** Transactional update of `flash_sale_campaigns.sold_quantity`.
- **Redis:** **NOT USED** for inventory tracking (pure DB logic).

**Your Innovation:**
Your new variant (e.g., Variant B) **MUST** use the same API and Schema as Variant Y, but you **MUST NOT** rely solely on slow DB transactions. You are expected to introduce caching, queuing, or other mechanisms (Redis, Memcached, etc.) to beat Variant Y's performance.

---

## 4. Complete Performance Comparison - All Variants

**Test Strategy:** Mixed (Fixed sweep + Adaptive plateau detection)
**Latest Test:** 2026-01-05
**Test Condition:** Sufficient inventory pre-loaded (50M items, no refills during test)

### Complete Performance Table

| Variant | API     | Service | Concurrency | Latency   | Throughput      |
|---------|---------|---------|-------------|-----------|-----------------|
| **HEALTH ENDPOINTS** |
| Y       | /health | Python  | c=460       | -         | 27,788 req/s    |
| Y       | /health | Java    | c=768       | -         | 188,205 req/s   |
| Y       | /health | C#      | c=2000      | -         | 358,676 req/s   |
| Y       | /health | Nginx   | c=100       | 9.64ms    | 9,862 req/s     |
| X       | /health | Python  | c=40        | 2.22ms    | 20,309 req/s    |
| X       | /health | Java    | c=921       | 4.80ms    | 190,509 req/s   |
| X       | /health | C#      | c=1280      | 3.80ms    | 390,184 req/s   |
| X       | /health | Nginx   | c=100       | 49.77ms   | 12,811 req/s    |
| A       | /health | Python  | c=500       | -         | 19,602 req/s    |
| A       | /health | Java    | c=300       | -         | 179,740 req/s   |
| A       | /health | C#      | c=300       | 19.62ms   | 292,930 req/s   |
| A       | /health | Nginx   | c=100       | 7.54ms    | 12,600 req/s    |
| **FLASH SALE ORDERS** |
| Y       | /orders | Python  | c=300       | 213.04ms  | 1,390 req/s ✓   |
| Y       | /orders | Java    | c=200       | 21.90ms   | 8,718 req/s ✓   |
| Y       | /orders | C#      | c=300       | 26.57ms   | 11,240 req/s ✓  |
| Y       | /orders | Nginx   | c=300       | 90.71ms   | 3,401 req/s     |
| X       | /orders | Python  | c=20        | 11.94ms   | 1,528 req/s     |
| X       | /orders | Java    | c=20        | 3.73ms    | 4,819 req/s     |
| X       | /orders | C#      | c=40        | 4.67ms    | 7,873 req/s     |
| X       | /orders | Nginx   | c=200       | 238.75ms  | 1,387 req/s     |
| A       | /orders | Python  | c=150       | 11.26ms   | 12,140 req/s    |
| A       | /orders | Java    | c=50        | 3.43ms    | 14,950 req/s    |
| A       | /orders | C#      | c=400       | 4.24ms    | **93,876 req/s** 👑 |
| A       | /orders | Nginx   | c=100       | 11.09ms   | 9,049 req/s     |

### Performance Rankings

**Flash Sale Orders (Production Workload):**
1. **C# Variant A - 93,876 req/s** @ c=400 👑
2. Java Variant A - 14,950 req/s @ c=50
3. Python Variant A - 12,140 req/s @ c=150
4. C# Variant Y - 11,240 req/s @ c=300
5. Nginx Variant A - 9,049 req/s @ c=100
6. Java Variant Y - 8,718 req/s @ c=200
7. C# Variant X - 7,873 req/s @ c=40
8. Java Variant X - 4,819 req/s @ c=20
9. Nginx Variant Y - 3,401 req/s @ c=300
10. Python Variant X - 1,528 req/s @ c=20
11. Python Variant Y - 1,390 req/s @ c=300
12. Nginx Variant X - 1,387 req/s @ c=200

---

## 5. Sacred Conventions & Idempotence

### ⚠️ CRITICAL: Understanding SACRED

**SACRED** = Self-verifying, Automated, Consistent, Reproducible, Explicit, Deterministic

**SACRED defines the schema standard.** All variants must use the same schema as Variant Y.

### SACRED VERIFICATION Command (Tests Environment Health via Variant Y)
```bash
bash scripts/verification/SACRED_VERIFICATION.sh
```

**This command validates the ENTIRE REPOSITORY ENVIRONMENT - it MUST be:**

1. **Idempotent:** Run it 100 times, get same result every time
   - No side effects that accumulate
   - No manual cleanup needed between runs
   - Safe to run in any state

2. **Self-Contained:** Works from clean slate
   - Starts services if not running
   - Seeds database if needed
   - Creates test data automatically

3. **Deterministic:** Always produces same outcome
   - Same test data every run
   - Same validation checks
   - Exit code 0 = success, non-zero = failure

4. **Comprehensive:** Verifies entire system
   - ✅ All containers running (Python, Java, C#, Nginx, MariaDB)
   - ✅ Health endpoints respond (200 OK)
   - ✅ Database connectivity
   - ✅ Order creation with SKU validation
   - ✅ Nginx load balancing

**Why Idempotence Matters:**
- Future agents can verify system without breaking anything
- No cleanup scripts needed
- Reproducible testing across environments
- Safe for automated CI/CD pipelines

### 🔥 CRITICAL: All Variant Tests Must Align with SACRED VERIFICATION Format

**All variant verification procedures MUST follow the exact same format as SACRED VERIFICATION.**

**Why This is Mandatory:**
1. **Performance Comparison:** Same test parameters enable direct variant-to-variant comparison
2. **Data Format Alignment:** Same CSV schema allows automated analysis across all variants
3. **Regression Detection:** Compare new variants against SACRED baseline
4. **Proof of Improvement:** Can definitively show "Variant X is 3x faster than Variant Y"

**What "Align with SACRED VERIFICATION" Means:**
- Same test sequence (4 steps: individual health → nginx health → individual orders → nginx orders)
- Same test parameters (same concurrency levels, duration, endpoints)
- Same data format (CSV schema matches SACRED VERIFICATION output)
- Same success criteria (same performance thresholds)

**Example - Why Alignment Enables Comparison:**
```bash
# Because both variants use same format, we can directly compare:
grep ",order," benchmark_results/variant_Y_raw_*.csv | awk -F',' '{print $3, $9}'
grep ",order," benchmark_results/variant_X_raw_*.csv | awk -F',' '{print $3, $9}'

# Result: Clear, quantifiable performance comparison
# Variant Y: csharp 1631 req/s
# Variant X: csharp 4200 req/s  → 2.6x performance improvement PROVEN
```

**Without format alignment:**
- Cannot compare performance (different test conditions)
- Cannot validate improvements (incompatible data)
- Cannot use standard analysis tools
- Cannot prove variant X is better than variant Y

**Full Conventions Document:** See `versions/CONVENTIONS.md` for complete sacred policies.

---

## 6. Quick Start (5 Minutes)

### Prerequisites
- Docker Desktop installed
- WSL2 (Windows) or native Linux
- 8GB+ RAM, 4+ CPU cores

### Start All Services
```bash
cd /home/syracuse/flashsale
docker compose up -d
sleep 30  # Wait for services to initialize
bash scripts/verification/SACRED_VERIFICATION.sh
```

**Expected output:** ✓ SACRED VERIFICATION PASSED

### Run Your First Benchmark
```bash
# Health endpoint test (fast, 2 minutes)
source lib/fixed_sweep.sh
run_fixed_sweep "variant_y" "python" "8000" "/health" "health" \
  "/tmp/my_first_test.csv"

# View results
cat /tmp/my_first_test.csv
```

---

## 7. Repository Structure & Navigation

### Key Directories

| Directory | Purpose | When to Use |
|-----------|---------|-------------|
| `docs/` | All documentation | Learning system architecture |
| `scripts/verification/` | Health checks | Verify services running correctly |
| `scripts/benchmarking/` | Performance tests | Run benchmark campaigns |
| `tools/` | Analysis utilities | Generate reports from raw CSV |
| `lib/` | Reusable test libraries | Import in custom scripts |
| `benchmark_results/campaigns/` | Test results | Compare performance across runs |
| `versions/` | Historical documentation | Understand system evolution |

### File Organization

```
/home/syracuse/flashsale/
├── README.md                       # This file
├── docker-compose.yml              # Service definitions (Variant Y)
│
├── python-service/                 # Variant Y Python Implementation
├── java-service/                   # Variant Y Java Implementation
├── csharp-service/                 # Variant Y C# Implementation
├── nginx/                          # Nginx Config
├── migrations/                     # Database Schema SQLs
│
├── scripts/                        # Operational scripts
│   ├── verification/               # SACRED_VERIFICATION.sh, etc.
│   ├── benchmarking/               # Performance testing
│   └── reproduction/
│
├── tools/                          # Analysis tools
│   ├── generate_summary_reports.sh
│   └── visualize_results.py
│
├── lib/                            # Reusable libraries
│   ├── wrk_parser.sh
│   ├── plateau_detector.sh
│   └── fixed_sweep.sh
│
├── versions/                       # Version history
│   ├── CONVENTIONS.md              # Sacred policies
│   └── [dated version files]
```

### Quick File Index
- **How to run benchmarks?** → `docs/QUICK_START.md`
- **Testing methodology?** → `docs/ADAPTIVE_TESTING.md`
- **Sacred conventions?** → `versions/CONVENTIONS.md`
- **Latest results?** → `benchmark_results/campaigns/[latest]/`
- **Verify services?** → `scripts/verification/SACRED_VERIFICATION.sh`
- **Reproduce variant Y?** → `scripts/reproduction/REPRODUCE_VARIANT_Y.sh`

---

## 8. Running Benchmarks (Step-by-Step)

### Strategy 1: Fixed Concurrency Sweep
**Use when:** You want to test specific concurrency levels (e.g., c=10, 25, 50, 100)

```bash
# Source the library
source lib/fixed_sweep.sh

# Test health endpoint
run_fixed_sweep "variant_y" "csharp" "8082" "/health" "health" \
  "benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign/raw/csharp_health.csv"

# Test order endpoint
run_fixed_sweep "variant_y" "csharp" "8082" "/api/v1/orders" "order" \
  "benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign/raw/csharp_orders.csv"
```

### Strategy 2: Adaptive Plateau Detection
**Use when:** You want to find optimal concurrency automatically

```bash
source lib/plateau_detector.sh

run_adaptive_test "variant_y" "java" "8081" "/health" "health" 10 \
  "benchmark_results/campaigns/$(date +%Y%m%d)_adaptive/raw/java_health.csv"
```

---

## 9. Implementing Your Own Variant - Guide for Newcomer Models

### Overview

This repository supports multiple architectural variants for performance comparison. Each variant implements the same API contracts but uses different internal strategies for inventory management.

### How to Implement a New Variant

#### Step 0: Critical Business Requirements (MUST IMPLEMENT)

**Flash Sale Campaign Business Logic - MANDATORY:**

1. **Campaign Pool Limit Enforcement (MUST)**
   - Each campaign has `total_sale_limit` (e.g., 1,000 items across ALL SKUs)
   - MUST decrement atomically when order succeeds
   - MUST reject orders when pool reaches 0
   - **Note:** Variant Y does this via DB Transactions. You may use Redis, Memcached, or other means.

2. **SKU Stock Validation (MUST)**
   - Each SKU has persistent inventory in database
   - MUST check stock > 0 before creating order
   - MUST decrement stock atomically

3. **Order Record Creation (MUST)**
   - Create `orders` record with status='created'
   - Create `order_line_items` record linking order to SKU
   - Create `payments` record (even if amount=0 for testing)
   - Return proper HTTP 201 with order_id

4. **Campaign Status API (MUST)**
   - Implement `GET /api/v1/campaigns/{id}/status`
   - Return: "Not Started", "Active", "Sold Out", "Ended"

#### Benchmark Scope vs. Production Reality

**You are building a Formula 1 engine, not a family sedan.**
Because this is a performance benchmark, you may make certain operational simplifications that would not be acceptable in production.

**✅ Permitted Simplifications:**
- **Manual Operations:** You can assume a human operator manually creates campaigns via SQL or runs a script to reconcile inventory after the sale. You do not need admin UIs or automated cron jobs.
- **"Happy Path" Focus:** You do not need complex automated failover or refund logic. If the system crashes during a benchmark, the test is simply voided.
- **Pre-Computation:** You may pre-calculate data (e.g., warm up caches) before the benchmark starts.

**❌ Forbidden Shortcuts:**
- **Skipping Validation:** You MUST check inventory and campaign limits for *every* request. Overselling is an immediate disqualification.
- **Hardcoded Responses:** You cannot return static JSON. You must actually create the order record in memory/DB/Redis.
- **Data Loss:** You cannot simply drop valid orders. If you accept an order (HTTP 201), it must be retrievable (in DB or a persistent queue).

**What You CAN Optimize (Your Innovation):**

- ✅ **HOW** you check campaign pool (Redis direct, RAM cache, pre-allocation, etc.)
- ✅ **WHEN** you decrement counters (eager, lazy, batch)
- ✅ **WHERE** inventory is cached (memory, Redis, both, neither)
- ✅ **Concurrency strategy** (locks, CAS, optimistic, pessimistic)
- ✅ **Refill strategy** (sync, async, predictive, reactive)

**Reference Implementation:**

- **Variant Y (Baseline):** You MAY copy the root `python-service`, `java-service`, and `csharp-service` folders to your `variant-{letter}/` directory as a starting scaffold.
- **STRICTLY FORBIDDEN to read:**
  - ❌ `/variant-x/` directory and all subdirectories
  - ❌ `/variant-a/` directory and all subdirectories
  - ❌ Any other `/variant-*/` directories

#### Step 1: Check Resource Allocation (AVOID CONFLICTS)

**CRITICAL:** Your new variant MUST use different ports, networks, and container names.

### Existing Variant Resource Allocation Table

| Variant | Network Subnet | MariaDB Port | Redis Port | Python Port | Java Port | C# Port | Nginx Port |
|---------|----------------|--------------|------------|-------------|-----------|---------|------------|
| **Y (SACRED)** | DNS-based | 3307 | (internal) | 8000 | 8081 | 8082 | 8443 |
| **X (Deprecated)** | 10.89.0.0/24 | 3312 | (internal) | 30011 | 8016 | 30012 | 8445 |
| **A (Corrected)** | 10.90.0.0/24 | 3313 | (internal) | 30013 | 8017 | 30014 | 8446 |

**Container Names in Use:**

| Service Type | Variant Y | Variant X | Variant A |
|--------------|-----------|-----------|-----------|
| Python | flash-python-y | flash-python-x | flash-python-a |
| Java | flash-java-y | flash-java-x | flash-java-a |
| C# | flash-csharp-y | flash-csharp-x | flash-csharp-a |
| MariaDB | flash-mariadb-y | flash-mariadb-x | flash-mariadb-a |
| Redis | (shared/internal) | flash-redis-x | flash-redis-a |
| Nginx | flash-nginx-y | flash-nginx-x | flash-nginx-a |

**DNS Hostnames (Internal Docker Networks):**

| Variant | MariaDB Host | Redis Host | Python Host | Java Host | C# Host |
|---------|--------------|------------|-------------|-----------|---------|
| Y | mariadb | (shared) | python | java | csharp |
| X | 10.89.0.2 | 10.89.0.3 | 10.89.0.4 | 10.89.0.5 | 10.89.0.6 |
| A | 10.90.0.2 | 10.90.0.3 | 10.90.0.4 | 10.90.0.5 | 10.90.0.6 |

**Next Available Resources (For Your Variant):**

If implementing Variant B (next):
- Network Subnet: **10.91.0.0/24** (increment pattern)
- MariaDB Port: **3314** (host) → Container: flash-mariadb-b
- Redis: **10.91.0.3** (internal)
- Python Port: **30015** (host) → Container: flash-python-b
- Java Port: **8018** (host) → Container: flash-java-b
- C# Port: **30016** (host) → Container: flash-csharp-b
- Nginx Port: **8447** (host) → Container: flash-nginx-b

**Allocation Pattern for Future Variants:**
- Network: `10.{90+N}.0.0/24` where N = variant index (A=0, B=1, C=2, ...)
- MariaDB: `33{13+N}` (A=3313, B=3314, C=3315, ...)
- Python: `300{13+2N}` (A=30013, B=30015, C=30017, ...)
- Java: `80{17+N}` (A=8017, B=8018, C=8019, ...)
- C#: `300{14+2N}` (A=30014, B=30016, C=30018, ...)
- Nginx: `84{46+N}` (A=8446, B=8447, C=8448, ...)

#### Step 2: Understand the SACRED Schema (MANDATORY)

**Before implementing ANY variant, you MUST:**
1. Read `versions/CONVENTIONS.md` completely
2. Understand that Variant Y defines the database schema (immutable)
3. Schema Source: `migrations/001_add_flash_sale_campaigns.sql`

#### Step 6: Implement in All Three Languages

**CRITICAL: Must implement Python, Java, AND C#**

Why all three?
- Performance comparison across language runtimes
- Validates architecture is language-independent
- Proves concepts work in different concurrency models

**Example Directory Structure:**
```
/home/syracuse/flashsale/variant-{your_letter}/
├── docker-compose.yml
├── python-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       └── main.py  # FastAPI implementation
├── java-service/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/java/com/flashsale/api/
│       ├── controller/OrderController.java
│       └── service/YourInventoryService.java
├── csharp-service/
│   ├── Dockerfile
│   ├── FlashSale.csproj
│   └── Controllers/
│       └── OrderController.cs
└── nginx/
    └── nginx.conf
```

#### Step 7: Create Verification Script

**Required:** `variant-{your_letter}/verify_variant_{your_letter}.sh`

**Use the provided template:**
```bash
cp scripts/verification/template_verify_variant.sh variant-{your_letter}/verify_variant_{your_letter}.sh
chmod +x variant-{your_letter}/verify_variant_{your_letter}.sh
```

**Customize the template:**
1. Open the script
2. Update the `CONFIGURATION` section (Container names, ports)
3. **Data Setup:** Use `python-service/setup_test_data.py` (from Variant Y) as your reference for seeding data.

**CSV Output Schema (MUST MATCH SACRED):**
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,
duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,
p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,
total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,
socket_errors_read,socket_errors_write,socket_errors_timeout,
transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
```

#### Step 4: The SACRED VERIFICATION Workflow

**MANDATORY Workflow (Never Skip):**

```bash
# 1. BEFORE making ANY changes
bash scripts/verification/SACRED_VERIFICATION.sh
# MUST PASS - establishes environmental baseline

# 2. Create your variant infrastructure
# ... implement services, docker-compose, etc.

# 3. Start your variant services
cd variant-{your_letter}
docker-compose up -d

# 4. CRITICAL: Run SACRED VERIFICATION again
bash ../scripts/verification/SACRED_VERIFICATION.sh
# MUST STILL PASS - proves no environmental interference

# 5. Once SACRED passes, verify your variant
bash verify_variant_{your_letter}.sh
```

---

## 10. Version History & Notes

### Version 2026-01-12: Variant A Record Performance

**What Changed:**
- Updated Variant A performance results
- C# Variant A achieves **93,876 req/s** - nearly meeting 100K goal
- Java Variant A achieves **14,950 req/s** with 3.43ms latency
- Python Variant A achieves **12,140 req/s**
- Nginx round-robin achieves **9,049 req/s** across 3 backends

**Performance Rankings Updated:**
1. C# Variant A - 93,876 req/s @ c=400 (NEW RECORD)
2. Java Variant A - 14,950 req/s @ c=50
3. Python Variant A - 12,140 req/s @ c=150

---

**Last Updated:** 2026-01-12
**Maintained By:** Syracuse
**Repository:** /home/syracuse/flashsale