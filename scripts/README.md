# Scripts Directory

Operational scripts for verification, benchmarking, and reproduction.

## Directory Structure

```
scripts/
├── verification/       # Health checks and system validation
├── benchmarking/       # Performance testing scripts
└── reproduction/       # Variant reproduction scripts
```

## Verification Scripts

### SACRED_VERIFICATION.sh
**Location:** `scripts/verification/SACRED_VERIFICATION.sh`

**Purpose:** Comprehensive system health check (SACRED = Self-verifying, Automated, Consistent, Reproducible, Explicit, Deterministic)

**Usage:**
```bash
bash scripts/verification/SACRED_VERIFICATION.sh
```

**What it checks:**
- ✅ All containers running (Python, Java, C#, Nginx, MariaDB)
- ✅ Health endpoints respond (200 OK)
- ✅ Database connectivity
- ✅ Order creation with SKU validation
- ✅ Nginx load balancing

**Exit codes:**
- `0` - All checks passed
- `1` - One or more checks failed

**Idempotence:** Safe to run 100 times - no side effects, no cleanup needed

### CORE_VERIFICATION.sh
**Location:** `scripts/verification/CORE_VERIFICATION.sh`

**Purpose:** Core service health checks only (subset of SACRED_VERIFICATION)

**Usage:**
```bash
bash scripts/verification/CORE_VERIFICATION.sh
```

### check_variant_y.sh
**Location:** `scripts/verification/check_variant_y.sh`

**Purpose:** Verify Variant Y specific configuration (no Redis, MariaDB-only)

**Usage:**
```bash
bash scripts/verification/check_variant_y.sh
```

## Benchmarking Scripts

### run_4step_benchmark.sh
**Location:** `scripts/benchmarking/run_4step_benchmark.sh`

**Purpose:** Execute 4-step benchmark process across all services

**Usage:**
```bash
bash scripts/benchmarking/run_4step_benchmark.sh
```

**Steps:**
1. Health endpoint verification
2. Order endpoint validation
3. Performance baseline establishment
4. Load testing

### run_complete_benchmark.sh
**Location:** `scripts/benchmarking/run_complete_benchmark.sh`

**Purpose:** Full benchmark suite including all services and endpoints

**Usage:**
```bash
bash scripts/benchmarking/run_complete_benchmark.sh [output_directory]
```

**Example:**
```bash
bash scripts/benchmarking/run_complete_benchmark.sh \
  benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign/raw/
```

### benchmark_plateau.sh
**Location:** `scripts/benchmarking/benchmark_plateau.sh`

**Purpose:** Run adaptive plateau detection benchmark

**Usage:**
```bash
bash scripts/benchmarking/benchmark_plateau.sh [service] [port] [endpoint]
```

**Example:**
```bash
bash scripts/benchmarking/benchmark_plateau.sh csharp 8082 /health
```

## Reproduction Scripts

### REPRODUCE_VARIANT_Y.sh
**Location:** `scripts/reproduction/REPRODUCE_VARIANT_Y.sh`

**Purpose:** Reproduce Variant Y from scratch

**Usage:**
```bash
bash scripts/reproduction/REPRODUCE_VARIANT_Y.sh
```

**What it does:**
1. Stops all running containers
2. Removes old data
3. Rebuilds services
4. Seeds database
5. Runs SACRED_VERIFICATION.sh
6. Executes baseline benchmarks

## Using Test Libraries

For more control, use test libraries directly:

### Fixed Sweep Testing
```bash
source lib/fixed_sweep.sh

run_fixed_sweep "variant_y" "csharp" "8082" "/health" "health" \
  "benchmark_results/campaigns/my_campaign/raw/csharp_health.csv"
```

### Adaptive Plateau Detection
```bash
source lib/plateau_detector.sh

run_adaptive_test "variant_y" "java" "8081" "/health" "health" 10 \
  "benchmark_results/campaigns/my_campaign/raw/java_health_adaptive.csv"
```

## Common Workflows

### 1. Verify System Before Testing
```bash
# Always run this first!
bash scripts/verification/SACRED_VERIFICATION.sh
```

### 2. Run Complete Benchmark Campaign
```bash
# Create campaign directory
CAMPAIGN="benchmark_results/campaigns/$(date +%Y%m%d)_my_campaign"
mkdir -p "$CAMPAIGN"/{raw,reports,visualizations}

# Run complete benchmark
bash scripts/benchmarking/run_complete_benchmark.sh "$CAMPAIGN/raw/"

# Generate reports
bash tools/generate_summary_reports.sh "$CAMPAIGN/raw/*.csv" \
  > "$CAMPAIGN/reports/summary.md"
```

### 3. Test Single Service
```bash
source lib/fixed_sweep.sh

# Test C# order endpoint
run_fixed_sweep "variant_y" "csharp" "8082" "/api/v1/orders" "order" \
  "/tmp/csharp_orders_test.csv"

# View results
cat /tmp/csharp_orders_test.csv
```

### 4. Reproduce Variant from Scratch
```bash
# Complete rebuild and verification
bash scripts/reproduction/REPRODUCE_VARIANT_Y.sh
```

## Script Conventions

All scripts in this directory follow these conventions:

1. **Idempotence:** Safe to run multiple times
2. **Exit codes:** 0 = success, non-zero = failure
3. **Output:** Clear status messages with ✓/✗ indicators
4. **Error handling:** Fail fast with descriptive error messages
5. **Sacred compliance:** Follow `/versions/CONVENTIONS.md` policies

## Troubleshooting

### Script fails with "permission denied"
```bash
chmod +x scripts/verification/SACRED_VERIFICATION.sh
```

### Script can't find docker containers
```bash
# Start all services first
docker compose up -d
sleep 30  # Wait for initialization
```

### Benchmark results look incorrect
```bash
# Verify services are healthy first
bash scripts/verification/SACRED_VERIFICATION.sh

# Check service logs
docker compose logs python-service
docker compose logs java-service
docker compose logs csharp-service
```

## See Also

- **Main README:** `/README.md` - Complete system documentation
- **Test Libraries:** `/lib/` - Reusable test functions
- **Analysis Tools:** `/tools/README.md` - Report generation utilities
- **Conventions:** `/versions/CONVENTIONS.md` - Sacred policies

---

**Last Updated:** 2026-01-02
**Maintained By:** Syracuse
