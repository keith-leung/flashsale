# Adaptive Plateau Detection Testing - Variant Y

## Overview

Variant Y now implements **intelligent adaptive plateau detection** for performance testing. This system dynamically adjusts test parameters based on real-time throughput analysis to find the true performance plateau or system peak.

**Key Principle:** NO QUICK MODE, EVER. Every test run performs comprehensive analysis to find the true plateau.

---

## Architecture

### Components

```
/home/syracuse/flashsale/
├── SACRED_VERIFICATION.sh          # Main entry point (always full mode)
├── lib/
│   ├── plateau_detector.sh        # Core adaptive testing algorithm
│   └── wrk_parser.sh              # Parse wrk output → CSV row
├── generate_pivot_summary.py      # CSV → Markdown summary
└── benchmark_results/
    ├── variant_Y_raw_YYYYMMDD_HHMMSS.csv    # Raw test data
    └── summary_YYYYMMDD_HHMMSS.md           # Pivot summary
```

### Data Flow

```
SACRED_VERIFICATION.sh
    ↓
Initialize CSV (with schema header)
    ↓
For each service/endpoint:
    ↓
    plateau_detector.sh
        ↓
        Run adaptive test loop:
            - Execute wrk
            - Parse output (wrk_parser.sh)
            - Analyze growth
            - Make decision
            - Adjust threads/concurrency
            - Write row to CSV
        ↓
        Until: PLATEAU_CONFIRMED | SYSTEM_LIMIT | MAX_CAPS_REACHED
    ↓
Generate pivot summary (generate_pivot_summary.py)
    ↓
Output: CSV raw data + Markdown summary
```

---

## Adaptive Testing Algorithm

### Starting Point
- **Threads:** 4
- **Concurrency:** 10
- **Duration:** Global parameter (default 10s, +5s for c>500, +10s for c>1000)

### Growth Analysis

After each test, calculate throughput increase percentage:

```
increase_pct = ((current_throughput - previous_throughput) / previous_throughput) × 100
```

### Decision Logic

| Condition | Decision | Action |
|-----------|----------|--------|
| First test | `INITIAL` | Baseline established |
| increase > 5% | `SIGNIFICANT_GROWTH` | Aggressive increase: t × 1.5, c × 2 |
| 2% ≤ increase ≤ 5% | `MODERATE_GROWTH` | Moderate increase: t × 1.2, c × 1.5 |
| 0% ≤ increase < 2% | `MARGINAL_GROWTH` | Small increase: t × 1.1, c × 1.2 |
| <2% variance across 3 tests | `PLATEAU_CONFIRMED` | **STOP** - True plateau found |
| Any 503 error | `SYSTEM_LIMIT` | **STOP** - System capacity reached |
| t=24 and c=2000 | `MAX_CAPS_REACHED` | **STOP** - Maximum caps hit |

### Plateau Confirmation

Plateau is confirmed when:
1. At least 3 consecutive tests have been performed
2. Throughput variance (coefficient of variation) < 2%
3. Formula: `CV = (stdev / mean) × 100 < 2%`

**Example:**
```
Test 7: 33,500 req/s
Test 8: 33,650 req/s  (+0.4%)
Test 9: 33,820 req/s  (+0.5%)
→ Variance: 0.47% < 2% → PLATEAU_CONFIRMED
```

### Error Policy

**Zero tolerance for 503 errors:**
- If ANY 503 error is detected → immediately stop
- Previous test configuration = safe maximum
- Decision: `SYSTEM_LIMIT`

---

## CSV Schema

All test results are written to a CSV file with the following schema:

```csv
timestamp,variant,service,endpoint,test_type,threads,concurrency,duration_s,
req_per_sec,avg_latency_ms,p50_latency_ms,p90_latency_ms,p99_latency_ms,
max_latency_ms,stdev_latency_ms,total_requests,total_errors,error_rate_pct,
non_2xx_3xx,socket_errors_connect,socket_errors_read,socket_errors_write,
socket_errors_timeout,transfer_mb,throughput_mb_s,test_sequence,
throughput_increase_pct,decision
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | UTC timestamp of test |
| `variant` | string | Variant name (e.g., "variant_y") |
| `service` | string | Service name (python, java, csharp, nginx) |
| `endpoint` | string | Endpoint path (e.g., "/health", "/api/v1/orders") |
| `test_type` | string | Type of test ("health" or "order") |
| `threads` | int | Number of wrk threads |
| `concurrency` | int | Number of concurrent connections |
| `duration_s` | int | Test duration in seconds |
| `req_per_sec` | float | Requests per second (throughput) |
| `avg_latency_ms` | float | Average latency in milliseconds |
| `p50_latency_ms` | float | 50th percentile latency |
| `p90_latency_ms` | float | 90th percentile latency |
| `p99_latency_ms` | float | 99th percentile latency |
| `max_latency_ms` | float | Maximum latency |
| `stdev_latency_ms` | float | Standard deviation of latency |
| `total_requests` | int | Total requests executed |
| `total_errors` | int | Total errors (all types) |
| `error_rate_pct` | float | Error rate percentage |
| `non_2xx_3xx` | int | Non-2xx/3xx HTTP responses |
| `socket_errors_connect` | int | Socket connection errors |
| `socket_errors_read` | int | Socket read errors |
| `socket_errors_write` | int | Socket write errors |
| `socket_errors_timeout` | int | Socket timeout errors |
| `transfer_mb` | float | Total data transferred (MB) |
| `throughput_mb_s` | float | Data throughput (MB/s) |
| `test_sequence` | int | Sequential test number |
| `throughput_increase_pct` | float | % increase vs previous test |
| `decision` | string | Algorithm decision |

---

## Usage

### Basic Usage (Default 10s Duration)

```bash
cd /home/syracuse/flashsale
bash SACRED_VERIFICATION.sh
```

### Custom Duration (e.g., 30s per test)

```bash
bash SACRED_VERIFICATION.sh 30
```

### Output Files

After completion, you'll find:

1. **CSV Raw Data:**
   ```
   ./benchmark_results/variant_Y_raw_20260102_143052.csv
   ```

2. **Pivot Summary:**
   ```
   ./benchmark_results/summary_20260102_143052.md
   ```

### View Results

```bash
# View CSV (formatted)
cat ./benchmark_results/variant_Y_raw_TIMESTAMP.csv | column -t -s,

# View summary
cat ./benchmark_results/summary_TIMESTAMP.md
```

---

## Pivot Summary

The `generate_pivot_summary.py` script analyzes CSV data and generates a comprehensive markdown report containing:

### 1. Executive Summary Table

Shows optimal configuration and peak performance for each service/endpoint:

```markdown
| Service | Endpoint | Type | Max Throughput | Optimal Config | Avg Latency | P90 Latency | P99 Latency | Result |
|---------|----------|------|----------------|----------------|-------------|-------------|-------------|--------|
| python  | /health  | health | 35,420 req/s | t=12 c=200 | 5.2ms | 8.1ms | 12.3ms | ✓ Plateau |
```

### 2. Detailed Test Progressions

Shows each test iteration with throughput increase and decision:

```markdown
| Test | Threads | Concurrency | Duration | Throughput | Avg Lat | P90 Lat | P99 Lat | Increase | Decision |
|------|---------|-------------|----------|------------|---------|---------|---------|----------|----------|
| 1    | 4       | 10          | 10s      | 12,500     | 0.8ms   | 1.2ms   | 2.1ms   | N/A      | INITIAL  |
| 2    | 4       | 25          | 10s      | 18,900     | 1.3ms   | 2.0ms   | 3.5ms   | +51.2%   | SIGNIFICANT_GROWTH |
```

### 3. Methodology Section

Explains the adaptive algorithm and decision types.

---

## Multi-Variant Comparison

The CSV schema is **consistent across all variants** (Y, X, Z, etc.), enabling easy comparison:

### Future: compare_variants.py

```bash
python3 compare_variants.py \
    ./benchmark_results/variant_Y_raw_20260102.csv \
    ./benchmark_results/variant_X_raw_20260102.csv
```

Output: Side-by-side comparison showing performance delta.

---

## Example Test Run Timeline

**Service:** Python health endpoint
**Base Duration:** 10s

```
Test 1: t=4   c=10   → 12,500 req/s  (N/A)          → INITIAL
Test 2: t=4   c=25   → 18,900 req/s  (+51.2%)       → SIGNIFICANT_GROWTH (aggressive)
Test 3: t=6   c=50   → 24,300 req/s  (+28.6%)       → SIGNIFICANT_GROWTH (aggressive)
Test 4: t=9   c=100  → 29,800 req/s  (+22.6%)       → SIGNIFICANT_GROWTH (aggressive)
Test 5: t=13  c=200  → 33,100 req/s  (+11.1%)       → SIGNIFICANT_GROWTH (aggressive)
Test 6: t=19  c=400  → 34,500 req/s  (+4.2%)        → MODERATE_GROWTH (moderate)
Test 7: t=22  c=600  → 35,200 req/s  (+2.0%)        → MODERATE_GROWTH (moderate)
Test 8: t=24  c=900  → 35,650 req/s  (+1.3%)        → MARGINAL_GROWTH (small)
Test 9: t=24  c=1080 → 35,820 req/s  (+0.5%)        → MARGINAL_GROWTH (small)

→ Variance across tests 7-9: 0.87% < 2%
→ PLATEAU_CONFIRMED at t=24, c=900, 35,650 req/s
```

**Total tests:** 9
**Total time:** ~2-3 minutes (accounting for warmup + pauses)

---

## Comparison: Old vs New

### Old Approach (Fixed Sweep)

```bash
# Fixed concurrency levels
CONCURRENCY_LEVELS=(10 25 50 75 100 150 200 300 400 500 750 1000)

# Fixed thread count
THREADS=12

# Fixed duration
DURATION=30s

# Problem: Wastes time testing beyond plateau
# Problem: Might miss optimal configuration between fixed levels
# Problem: No intelligent stopping criteria
```

**Issues:**
- Tests all 12 levels even after plateau detected
- Fixed t=12 might be too low or too high
- 30s × 12 levels = 6 minutes per endpoint
- No error handling for 503s

### New Approach (Adaptive)

```bash
# Dynamic adjustment based on growth
# Stops immediately when plateau confirmed
# Stops immediately on ANY 503 error
# Smart duration scaling

# Benefits: Finds plateau faster
# Benefits: No wasted tests
# Benefits: Optimal thread/concurrency pairing
```

**Advantages:**
- Typically finds plateau in 5-10 tests
- 10s × ~7 tests = ~70 seconds per endpoint
- **4-5x faster** than fixed sweep
- Graceful error handling

---

## Best Practices

### 1. Running Tests

- **Always use default duration (10s) for initial exploration**
- Use longer duration (30s+) only for:
  - Final validation runs
  - Publication-quality data
  - Comparing against external benchmarks

### 2. Interpreting Results

- **PLATEAU_CONFIRMED:** True sustainable throughput
- **MAX_CAPS_REACHED:** May have headroom, but capped for safety
- **SYSTEM_LIMIT:** True hardware/software limit (503 errors)

### 3. Comparing Variants

- Always run tests on same hardware
- Allow services to warm up before testing
- Run multiple times to confirm consistency
- Use CSV data for statistical analysis

---

## Troubleshooting

### Issue: Tests stop too early

**Symptom:** Only 2-3 tests before plateau detection

**Cause:** Very efficient service with genuine early plateau

**Solution:** Normal behavior - some endpoints plateau quickly

### Issue: Tests hit MAX_CAPS_REACHED

**Symptom:** Decision is always `MAX_CAPS_REACHED`

**Cause:** Service can handle more than t=24, c=2000

**Solution:** This is expected for high-performance services - caps prevent excessive resource usage

### Issue: All tests show SYSTEM_LIMIT

**Symptom:** First test already has 503 errors

**Cause:** Service overloaded, starting concurrency too high, or service not ready

**Solution:**
1. Verify services are healthy: `bash check_variant_y.sh`
2. Check logs: `docker logs flash-python-y`
3. Reduce starting concurrency in `lib/plateau_detector.sh`

### Issue: CSV file is empty

**Symptom:** No data in CSV besides header

**Cause:** Script error or wrk not installed

**Solution:**
1. Verify wrk installed: `which wrk`
2. Check script execution: add `set -x` to debug
3. Verify CSV write permissions

---

## Future Enhancements

### Planned Features

1. **compare_variants.py:**
   - Side-by-side variant comparison
   - Performance delta calculations (absolute + percentage)
   - Statistical significance testing

2. **Confidence Intervals:**
   - Run each configuration multiple times
   - Calculate mean + confidence intervals
   - Detect outliers

3. **Cost Analysis:**
   - Track test duration and resource usage
   - Calculate cost-per-request at each level
   - Optimize for cost/performance ratio

4. **Automated Reporting:**
   - Generate charts/graphs from CSV
   - Export to PDF
   - Email summaries

---

## References

- **SACRED_VERIFICATION.sh:** Main verification script
- **lib/plateau_detector.sh:** Core adaptive algorithm
- **lib/wrk_parser.sh:** WRK output parser
- **generate_pivot_summary.py:** Summary generator
- **VARIANT_Y_REDIS_REMOVAL.md:** Variant Y architecture

---

**Version:** 1.0
**Date:** 2026-01-02
**Status:** ✅ IMPLEMENTED
