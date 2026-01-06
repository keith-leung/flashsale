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
✅ Variant Y services: `python-service/`, `java-service/`, `csharp-service/`
✅ Database schema files
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
bash SACRED_VERIFICATION.sh  # Establishes environment baseline

# 2. Make your changes to Variant X (ports, Docker, resources, code)

# 3. After changes - Test environmental integrity
bash SACRED_VERIFICATION.sh  # CRITICAL TEST
    ↓
    FAILS? → Your changes BROKE THE ENVIRONMENT
            → Revert and fix infrastructure approach
    ↓
    PASSES? → Environment is still healthy
             → Safe to verify variant-specific functionality

# 4. Now test variant-specific functionality
bash verify_variant_x.sh
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
3. [Complete Performance Comparison - All Variants](#3-complete-performance-comparison---all-variants)
4. [Sacred Conventions & Idempotence](#4-sacred-conventions--idempotence)
5. [Quick Start (5 Minutes)](#5-quick-start-5-minutes)
6. [Repository Structure & Navigation](#6-repository-structure--navigation)
7. [Running Benchmarks](#7-running-benchmarks-step-by-step)
8. [Recording & Comparing Results](#8-recording--comparing-results)
9. [Understanding Test Strategies](#9-understanding-test-strategies)
10. [File Index](#10-file-index--where-to-find-things)
11. [Implementing Your Own Variant](#11-implementing-your-own-variant---guide-for-newcomer-models)
12. [Version History & Notes](#12-version-history--notes)

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
- **Redis:** (Removed in Variant Y) - No longer used

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

## 3. Complete Performance Comparison - All Variants

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
| A       | /orders | Python  | c=100       | 13.31ms   | 3,093 req/s     |
| A       | /orders | Java    | c=100       | 2.41ms    | 10,653 req/s    |
| A       | /orders | C#      | c=150       | 3.66ms    | **39,586 req/s** 👑 |
| A       | /orders | Nginx   | c=100       | 99.97ms   | 1,512 req/s     |

**⚠️ Note on Previous Results:** Earlier tests used conservative concurrency levels (c=68 for Python Y, c=96 for Java Y, c=48 for C# Y), significantly understating performance. Updated tests with proper concurrency (c=300, c=200, c=300) revealed:
- Python Y: 711→1,390 req/s (+95%)
- Java Y: 4,139→8,718 req/s (+110%)
- C# Y: 9,221→11,240 req/s (+22%)

### Performance Rankings

**Flash Sale Orders (Production Workload):**
1. **C# Variant Y - 11,240 req/s** @ c=300 👑
2. Java Variant A - 10,653 req/s @ c=100
3. Java Variant Y - 8,718 req/s @ c=200
4. C# Variant X - 7,873 req/s @ c=40
5. Java Variant X - 4,819 req/s @ c=20
6. Nginx Variant Y - 3,401 req/s @ c=300
7. Python Variant A - 3,093 req/s @ c=100
8. Python Variant X - 1,528 req/s @ c=20
9. Nginx Variant A - 1,512 req/s @ c=100
10. Python Variant Y - 1,390 req/s @ c=300
11. Nginx Variant X - 1,387 req/s @ c=200

### Key Findings

**1. C# Variant Y Achieves Highest Throughput**
- At conservative c=48: 9,221 req/s
- At optimal c=300: **11,240 req/s** (+22%)
- Demonstrates .NET's superior async I/O and database handling

**2. Java Variant A Achieves Lowest Latency**
- 10,653 req/s @ c=100
- Latency: 2.41ms (vs C# Y's 26.57ms)
- Different architectural trade-off from Variant Y

**3. Concurrency Tuning is Critical**
- Under-testing hides true performance (Java Y was underestimated by 110%)
- Each service has different optimal concurrency
- Proper load testing reveals actual production capacity

**4. Architecture vs Language Performance**
- **Best throughput:** C# Y - 11,240 req/s @ c=300
- **Best latency:** Java A - 2.41ms @ c=100
- **Most scalable:** Nginx load balancing enables horizontal scaling

**5. Business Logic Overhead Analysis**
Comparing /health (minimal logic) vs /orders (full processing):
- Java /health: 179K req/s (empty response)
- Java /orders (best variant): 10K req/s (full order processing)
- **Gap: 17x overhead from business logic**

Order processing overhead includes:
- JSON parsing/serialization
- Database transactions
- Order entity creation + validation
- Payment record creation
- Multiple service layer calls
- Response DTO building

**The bottleneck is application logic, not external I/O!**

**6. Gap to Performance Goal**
- **Performance Goal:** 100,000 req/s (single service)
- **Best Single Service:** 11,240 req/s (C# Y)
- **Gap Remaining:** 8.9x improvement needed
- **Horizontal Scaling Path:** 3,401 req/s (Nginx) × 30 backends = 102,030 req/s ✓

---

## 4. Sacred Conventions & Idempotence

### ⚠️ CRITICAL: Understanding SACRED

**SACRED is the golden standard defined by Variant Y. ALL variants must align with SACRED.**

- ✅ **Variant Y:** Defines the SACRED schema (golden standard, immutable)
- ✅ **Variant X:** Must align with SACRED schema (same database schema, same API contracts)
- ✅ **All other variants:** Must align with SACRED schema (implementation can vary, schema cannot)

### 🔥 SACRED VERIFICATION = Repository-Wide Unit Test

**SACRED VERIFICATION is the unit test for the ENTIRE REPOSITORY, not just Variant Y.**

**Critical Understanding:**
- Tests variant Y (simplest, most stable implementation)
- **Validates the entire environment** (database, network, ports, Docker, resources)
- If SACRED VERIFICATION fails → **the environment approach is wrong**

**Why This Matters:**
```
Make changes to Variant X (new ports, Docker config, resources)
    ↓
Run SACRED VERIFICATION
    ↓
    FAILS? → Variant X changes broke the environment
            → Fix environment configuration before proceeding
    ↓
    PASSES? → Environment is healthy
             → Safe to verify Variant X specifically
```

**SACRED VERIFICATION tests environmental integrity:**
- ✅ Port conflicts and network configuration
- ✅ Database connectivity across all services
- ✅ Docker container orchestration
- ✅ Resource allocation (CPU, memory)
- ✅ Service dependencies and startup order

**The Workflow:**
1. Make changes to ANY variant (X, Z, etc.)
2. Run SACRED VERIFICATION **first** (validates environment)
3. If SACRED passes → Run variant-specific verification
4. If SACRED fails → Environment is broken, fix infrastructure

**Variant Y is the canary in the coal mine** - if the simplest implementation can't run, the environment is misconfigured.

### What is SACRED?
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

## 5. Quick Start (5 Minutes)

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

## 6. Repository Structure & Navigation

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
├── docker-compose.yml              # Service definitions
│
├── docs/                           # Documentation
│   ├── QUICK_START.md
│   ├── ADAPTIVE_TESTING.md
│   └── architecture/
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
├── benchmark_results/              # Test results
│   └── campaigns/
│       └── 20260102_fixed_sweep/  # Latest results
│
├── versions/                       # Version history
│   ├── CONVENTIONS.md              # Sacred policies
│   └── [dated version files]
│
├── python-service/                 # Service implementations
├── java-service/
├── csharp-service/
└── nginx/
```

### Quick File Index
- **How to run benchmarks?** → `docs/QUICK_START.md`
- **Testing methodology?** → `docs/ADAPTIVE_TESTING.md`
- **Sacred conventions?** → `versions/CONVENTIONS.md`
- **Latest results?** → `benchmark_results/campaigns/[latest]/`
- **Verify services?** → `scripts/verification/SACRED_VERIFICATION.sh`
- **Reproduce variant Y?** → `scripts/reproduction/REPRODUCE_VARIANT_Y.sh`

---

## 7. Running Benchmarks (Step-by-Step)

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

### Campaign Organization Template
```bash
# Create new campaign directory
CAMPAIGN_DIR="benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign"
mkdir -p "$CAMPAIGN_DIR"/{raw,reports,visualizations}

# Run tests (save to raw/)
# Generate reports (save to reports/)
# Create charts (save to visualizations/)
```

---

## 8. Recording & Comparing Results

### After Running Tests

1. **Organize raw data:**
   ```bash
   mv /tmp/*.csv benchmark_results/campaigns/[campaign]/raw/
   ```

2. **Generate summary report:**
   ```bash
   bash tools/generate_summary_reports.sh \
     benchmark_results/campaigns/[campaign]/raw/full_data.csv \
     > benchmark_results/campaigns/[campaign]/reports/summary.md
   ```

3. **Create campaign README** (copy template):
   ```markdown
   # Campaign: My Test Campaign
   Date: 2026-01-02
   Variant: Y
   
   ## Objective
   [Why this test was run]
   
   ## Results Summary
   - Python: X req/s (health), Y req/s (orders)
   - Java: X req/s (health), Y req/s (orders)
   - C#: X req/s (health), Y req/s (orders)
   
   ## Key Findings
   [What did we learn?]
   ```

### Comparing Across Campaigns

```bash
# Extract peak performance from all campaigns
awk -F',' 'NR>1 && $5=="health" {print $3, $9}' \
  benchmark_results/campaigns/*/raw/*.csv | sort -k2 -n

# Compare specific concurrency level
grep ",50," benchmark_results/campaigns/*/raw/csharp_health.csv
```

---

## 9. Understanding Test Strategies

### Fixed Sweep Strategy

**Concurrency Levels:**
- Health endpoints: c=10, 25, 50, 100, 200, 400, 800 (10s duration)
- Order endpoints: c=10, 25, 50, 100, 150, 200, 300 (15s duration)
- Nginx: c=10, 25, 50, 100, 200 (10s/15s duration)

**Threads:** Adaptive (min(12, concurrency))

**When to use:** Consistent comparison across runs, specific load testing

### Adaptive Plateau Strategy

**Algorithm:**
- Start: t=4, c=10
- >5% growth → increase aggressively (t×1.5, c×2)
- 2-5% growth → increase moderately (t×1.2, c×1.5)
- <2% growth → plateau candidate (t×1.1, c×1.2)
- <2% variance across 3 tests → PLATEAU CONFIRMED

**When to use:** Finding optimal configuration, unknown system limits

---

## 10. File Index & Where to Find Things

### Documentation
- System overview → This README.md
- Quick start guide → `docs/QUICK_START.md`
- Testing methodology → `docs/ADAPTIVE_TESTING.md`
- Sacred conventions → `versions/CONVENTIONS.md`
- Architecture details → `docs/architecture/IMPLEMENTATION_SUMMARY.md`

### Scripts & Tools
- Verification → `scripts/verification/SACRED_VERIFICATION.sh`
- Benchmarking → `scripts/benchmarking/run_4step_benchmark.sh`
- Analysis → `tools/generate_summary_reports.sh`
- Libraries → `lib/fixed_sweep.sh`, `lib/plateau_detector.sh`

### Results & Comparisons
- Latest results → `benchmark_results/campaigns/[latest]/`
- Historical results → `benchmark_results/campaigns/archive/`
- Full result data → See campaign `raw/` directories

### Advanced Topics

**CSV Output Schema:**
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,
duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,
p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,
total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,
socket_errors_read,socket_errors_write,socket_errors_timeout,
transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Start services | `docker compose up -d` |
| Verify services | `bash scripts/verification/SACRED_VERIFICATION.sh` |
| Fixed sweep test | `source lib/fixed_sweep.sh && run_fixed_sweep ...` |
| Adaptive test | `source lib/plateau_detector.sh && run_adaptive_test ...` |
| Generate report | `bash tools/generate_summary_reports.sh input.csv > output.md` |
| Compare results | `grep "pattern" benchmark_results/campaigns/*/raw/*.csv` |

---

## For More Information

- Architecture details → `docs/architecture/IMPLEMENTATION_SUMMARY.md`
- Testing methodology → `docs/ADAPTIVE_TESTING.md`
- Deployment guide → `versions/DEPLOYMENT.md`
- Version history → `versions/20260102_adaptive_plateau_detection.md`

---

## 11. Implementing Your Own Variant - Guide for Newcomer Models

### Overview

This repository supports multiple architectural variants for performance comparison. Each variant implements the same API contracts but uses different internal strategies for inventory management.

**Existing Variants:**
- **Variant Y (SACRED Baseline):** Reference implementation, defines schema
- **Variant X (Experimental):** Performance: 1,528 req/s (Python), 4,819 req/s (Java), 7,873 req/s (C#)
- **Variant A (Production):** Performance: 3,093 req/s (Python), 10,653 req/s (Java)

### How to Implement a New Variant

#### Step 0: Critical Business Requirements (MUST IMPLEMENT)

**Flash Sale Campaign Business Logic - MANDATORY:**

These are the core business rules ALL variants MUST implement. You cannot optimize away these requirements:

1. **Campaign Pool Limit Enforcement (MUST)**
   - Each campaign has `total_sale_limit` (e.g., 1,000 items across ALL SKUs)
   - MUST decrement atomically when order succeeds
   - MUST reject orders when pool reaches 0
   - Key: `fs:{campaign_id}:limit` in Redis

2. **SKU Stock Validation (MUST)**
   - Each SKU has persistent inventory in database
   - MUST check stock > 0 before creating order
   - MUST decrement stock atomically
   - Database table: `inventory.quantity`

3. **Order Record Creation (MUST)**
   - Create `orders` record with status='created'
   - Create `order_line_items` record linking order to SKU
   - Create `payments` record (even if amount=0 for testing)
   - Return proper HTTP 201 with order_id

4. **Campaign Status API (MUST)**
   - Implement `GET /api/v1/campaigns/{id}/status`
   - Return: "Not Started", "Active", "Sold Out", "Ended"
   - Calculate `remaining` from Redis pool

**What You CAN Optimize (Your Innovation):**

These are WHERE you implement your architectural creativity:

- ✅ **HOW** you check campaign pool (Redis direct, RAM cache, pre-allocation, etc.)
- ✅ **WHEN** you decrement counters (eager, lazy, batch)
- ✅ **WHERE** inventory is cached (memory, Redis, both, neither)
- ✅ **Concurrency strategy** (locks, CAS, optimistic, pessimistic)
- ✅ **Refill strategy** (sync, async, predictive, reactive)

**What You DON'T Need to Implement (Optional):**

- ❌ Complete order lifecycle (payment processing, shipping, etc.)
- ❌ Audit logging for compliance (add if you want, not required)
- ❌ Failover handling (focus on performance, not HA)
- ❌ Monitoring/observability (nice-to-have)
- ❌ Order cancellation/refunds
- ❌ Complex business rules (discounts, coupons, etc.)

**Reference Implementation:**

- **ONLY look at Variant Y** for schema and business logic: Main service directories `python-service/`, `java-service/`, `csharp-service/`
- **STRICTLY FORBIDDEN to read:**
  - ❌ `/variant-x/` directory and all subdirectories
  - ❌ `/variant-a/` directory and all subdirectories
  - ❌ Any other `/variant-*/` directories
  - ❌ Implementation details, architecture docs, or code from other variants
- **You may ONLY read:**
  - ✅ Root README.md (this file)
  - ✅ `versions/CONVENTIONS.md` (schema definitions)
  - ✅ Variant Y services: `python-service/`, `java-service/`, `csharp-service/`
  - ✅ Database schema files
  - ✅ Performance comparison tables (numbers only, no implementation details)

**Why This Restriction:**
- Each variant represents original research and innovation
- Copying defeats the purpose of performance comparison
- Your variant must demonstrate YOUR architectural thinking
- Performance improvements must come from YOUR innovations, not copying others

#### Step 1: Check Resource Allocation (AVOID CONFLICTS)

**CRITICAL: All existing variant resource allocations are listed below. Your new variant MUST use different ports, networks, and container names.**

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
3. All new variants MUST align with SACRED schema
4. Run SACRED VERIFICATION before and after your changes

**SACRED Schema Includes:**
- Database tables: `spus`, `skus`, `inventory`, `orders`, `order_line_items`, `payments`, `flash_sale_campaigns`, `flash_sale_campaign_skus`
- Redis keys: `fs:{campaign_id}:limit` for campaign pool tracking
- API contracts: `POST /api/v1/orders`, `GET /api/v1/campaigns/{id}/status`

#### Step 3: Choose Your Variant Letter

Pick an unused letter: **B, C, D, E, ..., Z**
- Variant Y = SACRED baseline (immutable)
- Variant X = Experimental (deprecated)
- Variant A = Corrected producer-consumer
- Your variant = Next available letter

#### Step 4: Create Isolated Infrastructure

**Network Isolation (CRITICAL):**
```yaml
# variant-{your_letter}/docker-compose.yml
networks:
  flash-network-{your_letter}:
    driver: bridge
    ipam:
      config:
        - subnet: 10.{90+N}.0.0/24  # N = your variant number
```

**Port Allocation (No Conflicts):**
```yaml
services:
  flash-python-{your_letter}:
    ports:
      - "300{XX}:8000"  # XX = unique port offset
  flash-java-{your_letter}:
    ports:
      - "80{YY}:8080"   # YY = unique port offset
  flash-csharp-{your_letter}:
    ports:
      - "300{ZZ}:80"    # ZZ = unique port offset
  flash-mariadb-{your_letter}:
    ports:
      - "33{NN}:3306"   # NN = unique port (e.g., 3314, 3315)
  flash-nginx-{your_letter}:
    ports:
      - "84{MM}:443"    # MM = unique port (e.g., 8447, 8448)
```

**Container Naming:**
```yaml
container_name: flash-{service}-{your_letter}
# Examples: flash-python-b, flash-java-b, flash-mariadb-b
```

#### Step 5: Implement Your Architecture

**Required Components (Per Service):**

1. **Order Service** (implements `/api/v1/orders`)
   - Must validate SKU exists and has stock
   - Must check campaign limits if SKU is in active campaign
   - Must create order, line items, payment records
   - Must return proper HTTP status codes (201/400/409/503)

2. **Campaign Service** (implements `/api/v1/campaigns/{id}/status`)
   - Must return real-time campaign status
   - Statuses: "Not Started", "Active", "Sold Out", "Ended"

3. **Health Endpoint** (`/health`)
   - Must return HTTP 200 with empty or minimal response
   - Used for infrastructure baseline testing

**Your Architectural Innovation:**

You can ONLY study Variant Y's implementation to understand the baseline approach. All other variants' implementations are strictly off-limits.

**Example Innovations to Explore (Do Your Own Research):**
- Caching strategies at different layers
- Concurrency control mechanisms
- Inventory allocation techniques
- Async processing patterns
- Distributed system coordination approaches
- Database optimization strategies
- Memory management approaches

**IMPORTANT:** These are general categories only. DO NOT read other variant directories to see HOW they implemented these concepts. Your solution must be based on YOUR research and architectural thinking, not copied from existing variants.

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

Must follow SACRED VERIFICATION format:
```bash
#!/bin/bash
# 1. Start services
# 2. Health checks
# 3. Test order creation
# 4. Run benchmarks (same methodology as SACRED)
# 5. Generate CSV output (SACRED schema)
# 6. Return exit code (0 = success, non-zero = failure)
```

**CSV Output Schema (MUST MATCH SACRED):**
```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,
duration_s,req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,
p99_latency_ms,max_latency_ms,stdev_latency_ms,total_requests,
total_errors,error_rate_pct,non_2xx_3xx,socket_errors_connect,
socket_errors_read,socket_errors_write,socket_errors_timeout,
transfer_mb,throughput_mb_s,test_sequence,throughput_increase_pct,decision
```

#### Step 8: The SACRED VERIFICATION Workflow

**MANDATORY Workflow (Never Skip):**

```bash
# 1. BEFORE making ANY changes
cd /home/syracuse/flashsale
bash scripts/verification/SACRED_VERIFICATION.sh
# MUST PASS - establishes environmental baseline

# 2. Create your variant infrastructure
mkdir variant-{your_letter}
# ... implement services, docker-compose, etc.

# 3. Start your variant services
cd variant-{your_letter}
docker-compose up -d

# 4. CRITICAL: Run SACRED VERIFICATION again
cd /home/syracuse/flashsale
bash scripts/verification/SACRED_VERIFICATION.sh
# MUST STILL PASS - proves no environmental interference

# 5. If SACRED VERIFICATION fails:
#    → Your variant broke the environment (ports, network, resources)
#    → Fix your variant's infrastructure
#    → DO NOT proceed until SACRED passes

# 6. Once SACRED passes, verify your variant
cd variant-{your_letter}
bash verify_variant_{your_letter}.sh

# 7. Benchmark your variant
source ../lib/fixed_sweep.sh
run_fixed_sweep "variant_{your_letter}" "python" "{port}" "/api/v1/orders" \
  "order" "benchmark_results/variant_{your_letter}_orders.csv"
```

#### Step 9: Compare Performance

**Add your results to the comparison table:**

```bash
# Extract peak performance
grep ",order," benchmark_results/variant_{your_letter}_*.csv | \
  awk -F',' '{print $3, $9}' | sort -k2 -n | tail -1

# Compare to baseline
echo "Variant Y (C#): 11,240 req/s"
echo "Your Variant:   ??? req/s"
```

#### Step 10: Document Your Variant

**Required Documentation:**

1. **Implementation Summary** (`variant-{your_letter}/README.md`)
   ```markdown
   # Variant {Your_Letter}: {Your Architecture Name}

   ## Architecture Overview
   [Explain your approach]

   ## Key Innovations
   - Innovation 1: ...
   - Innovation 2: ...

   ## Performance Results
   - Python: X req/s
   - Java: Y req/s
   - C#: Z req/s

   ## Comparison to Baselines
   - vs Variant Y: +X%
   - vs Variant A: +Y%
   ```

2. **Update Main README** (this file)
   - Add row to performance comparison table
   - Update rankings if your variant wins

3. **Version Note** (create `versions/20260105_variant_{your_letter}.md`)
   - Document design decisions
   - Explain trade-offs
   - Record benchmark methodology

### Common Pitfalls to Avoid

**❌ DON'T:**
- Modify Variant Y schema (breaks SACRED principle)
- Reuse ports from other variants (causes conflicts)
- Skip SACRED VERIFICATION before/after (misses environmental issues)
- Use different API endpoints (breaks compatibility)
- Implement only one language (incomplete comparison)
- Use different test methodology (incomparable results)

**✅ DO:**
- Follow SACRED schema exactly (same tables, same contracts)
- Isolate infrastructure (unique network, ports, containers)
- Run SACRED VERIFICATION first (establishes baseline)
- Implement all three languages (complete comparison)
- Use identical test methodology (comparable results)
- Document design decisions (future models benefit)

### Success Criteria

Your variant implementation is complete when:
- ✅ SACRED VERIFICATION passes before and after your changes
- ✅ All three services (Python, Java, C#) implement the API
- ✅ Benchmarks run using SACRED methodology
- ✅ CSV output matches SACRED schema
- ✅ Performance results added to main comparison table
- ✅ Documentation written (README + version note)
- ✅ No port conflicts or resource interference
- ✅ Can run alongside Variant Y without issues

**Welcome to the performance optimization challenge! May your variant be the fastest! 🚀**

---

## 12. Version History & Notes

### Version 2026-01-05: Comprehensive Performance Analysis

**What Changed:**
- Added complete Nginx round-robin benchmarks for all variants
- Corrected Variant Y concurrency levels (revealed 2x underestimation)
- Comprehensive cross-variant performance table (22 data points)
- Implementation guide for newcomer models

**Key Discoveries:**
- **C# Variant Y wins overall:** 11,240 req/s @ c=300 (previously 9,221 @ c=48)
- **Java Variant A best latency:** 2.41ms vs C# Y's 26.57ms
- **Concurrency tuning critical:** Under-testing can underestimate by 110%
- **Business logic is bottleneck:** Not Redis (17x gap between /health and /orders)

**Performance Rankings Updated:**
1. C# Variant Y - 11,240 req/s @ c=300
2. Java Variant A - 10,653 req/s @ c=100
3. Java Variant Y - 8,718 req/s @ c=200

**Methodology Improvements:**
- Pre-load 50M items to eliminate refill interference
- Test multiple concurrency levels to find true peak
- Include Nginx results for cluster scalability assessment

**Files Added:**
- `/tmp/test_variant_y_high_concurrency.sh` - Proper concurrency testing
- `/tmp/test_nginx_all_variants.sh` - Nginx benchmark suite
- Implementation guide in main README.md

### Version 2026-01-04: Java Variant A Implementation

**What Changed:**
- Implemented Java Variant A
- Fixed 3 critical bugs (YAML escaping, MariaDB auth, database config)
- Achieved 10,653 req/s (3.74x faster than Python A)
- Implementation details in `/variant-a/` directory

**Bugs Fixed:**
1. YAML password escaping (`!` requires quotes)
2. MariaDB wildcard users (created IP-specific users)
3. Database configuration decimal error

**Files Created:**
- 6 new Java files (840+ lines)
- 4 benchmark scripts
- 4 analysis reports

### Version 2026-01-03: Python Variant A Implementation

**What Changed:**
- Implemented Python Variant A
- Achieved 3,093 req/s (3.24x faster than Python Y)
- Implementation details in `/variant-a/` directory

### Version 2026-01-02: SACRED Methodology & Variant Y Baseline

**What Changed:**
- Established SACRED verification as repository-wide unit test
- Documented conventions in `versions/CONVENTIONS.md`
- Baseline performance: C# Y 1,642 req/s (later corrected to 11,240)

---

**Last Updated:** 2026-01-05
**Maintained By:** Syracuse
**Repository:** /home/syracuse/flashsale
