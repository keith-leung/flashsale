# Flashsale Benchmark Testing Repository

> **For New Agents:** Start here. This README contains everything you need to understand, run, and record benchmark tests.

## Table of Contents
1. [Business Requirements & System Logic](#1-business-requirements--system-logic)
2. [API Design](#2-api-design)
3. [Current Performance (Variant Y)](#3-current-performance-variant-y)
4. [Sacred Conventions & Idempotence](#4-sacred-conventions--idempotence)
5. [Quick Start (5 Minutes)](#5-quick-start-5-minutes)
6. [Repository Structure & Navigation](#6-repository-structure--navigation)
7. [Running Benchmarks](#7-running-benchmarks-step-by-step)
8. [Recording & Comparing Results](#8-recording--comparing-results)
9. [Understanding Test Strategies](#9-understanding-test-strategies)
10. [File Index](#10-file-index--where-to-find-things)

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

## 3. Current Performance (Variant Y)

### Latest Benchmark Results (2026-01-02 - Optimized Configuration)
**Test Strategy:** Adaptive plateau detection
**Test Date:** 2026-01-02 11:25 UTC
**Raw Data:** `benchmark_results/variant_Y_raw_20260102_112505.csv`

**Configuration Optimizations Applied:**
- Docker CPU limits increased (MariaDB: 16 cores, Services: 8-12 cores each)
- Java HikariCP connection pool: 200 connections (was 10 default)
- Python workers: Fixed at 16 (matches 8 CPU × 2)
- Python connection pool: 10 per worker + 5 overflow
- C# connection pool: 300 max connections
- Java JVM: G1GC tuning with 2-3G heap

#### Health Endpoints - Sustained Plateau Performance

| Service | **Plateau Throughput** | Optimal Concurrency | Avg Latency | p99 Latency |
|---------|------------------------|---------------------|-------------|-------------|
| **C#**     | **378,580 req/s** | c=1536 | 4.37ms | 9.28ms |
| **JAVA**   | **183,361 req/s** | c=2000 | 11.40ms | 18.64ms |
| **PYTHON** | **31,368 req/s**  | c=96   | 6.37ms | 38.92ms |
| **NGINX**  | **11,380 req/s**  | c=96   | 7.30ms | 10.01ms |

#### Order Endpoints - Sustained Plateau Performance (CORE METRIC)

| Service | **Plateau Throughput** | Optimal Concurrency | Avg Latency | p99 Latency | Timeouts |
|---------|------------------------|---------------------|-------------|-------------|----------|
| **C#**     | **1,631 req/s** | c=28  | 14.70ms | 21.43ms | 0 |
| **JAVA**   | **800 req/s**   | c=48  | 56.14ms | 101.68ms | 0 |
| **PYTHON** | **536 req/s**   | c=68  | 116.91ms | 265.69ms | 0 |
| **NGINX**  | **1,266 req/s** | c=144 | 123.40ms | 438.10ms | 0 |

#### Key Findings - This is the Baseline to Beat

**1. Database Operations are the Primary Bottleneck**
- Health endpoints (no DB): 31K-378K req/s
- Order endpoints (with DB): 536-1,631 req/s
- **Performance gap: 58x-232x slower with database operations**
- Connection pools and CPU limits are NO LONGER bottlenecks

**2. Service Performance Hierarchy**
- **C# leads:** 1,631 req/s for orders (baseline champion)
- **Java improved dramatically:** From 427→800 req/s (+87% after connection pool fix)
- **Python improved significantly:** From 361→536 req/s (+48% after worker/pool tuning)
- **Nginx adds value:** 1,266 req/s with load balancing across all backends

**3. System is Properly Utilizing Resources**
- All services hit sustained plateaus (not artificial CPU/connection limits)
- Zero timeouts across all order processing tests
- Latency stable and predictable at plateau points

**4. Gap to Goal**
- **Current Best:** 1,631 req/s (C# orders)
- **Performance Goal:** 100,000 req/s
- **Gap Remaining:** **61x improvement needed**

**Challenge to Future Variants:** Can you beat 1,631 req/s for order processing?
The bottleneck is now database query performance, not application configuration.

---

## 4. Sacred Conventions & Idempotence

### What is SACRED?
**SACRED** = Self-verifying, Automated, Consistent, Reproducible, Explicit, Deterministic

### Sacred Verification Command
```bash
bash scripts/verification/SACRED_VERIFICATION.sh
```

**This command is SACRED - it MUST be:**

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

**Last Updated:** 2026-01-02  
**Maintained By:** Syracuse  
**Repository:** /home/syracuse/flashsale
