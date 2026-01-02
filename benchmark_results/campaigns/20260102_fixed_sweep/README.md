# Campaign: Fixed Concurrency Sweep - Variant Y

**Date:** 2026-01-02
**Variant:** Y (No Redis, MariaDB-only)
**Services Tested:** Python, Java, C#, Nginx
**Test Strategy:** Fixed concurrency sweep

## Objective

Establish baseline performance metrics for Variant Y across all services using fixed concurrency levels. This campaign provides:
- Peak throughput identification for each service
- Optimal concurrency level determination
- Service comparison for production deployment decisions
- Baseline data for future variant comparisons

## Test Configuration

### Test Strategy: Fixed Concurrency Sweep

**Health Endpoints:**
- Concurrency levels: c=10, 25, 50, 100, 200, 400, 800
- Duration: 10 seconds per test
- Threads: Adaptive (min(12, concurrency))

**Order Endpoints:**
- Concurrency levels: c=10, 25, 50, 100, 150, 200, 300
- Duration: 15 seconds per test
- Threads: Adaptive (min(12, concurrency))

**Nginx (Load Balancer):**
- Concurrency levels: c=10, 25, 50, 100, 200
- Duration: 10s (health), 15s (orders)
- Round-robin distribution to backend services

## Results Summary

### Health Endpoints - Peak Performance

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts | Notes |
|---------|-----------------|---------------------|----------------|-------|
| PYTHON  | 15,728 req/s    | c=10                | 0              | Good low concurrency |
| JAVA    | 130,623 req/s   | c=100               | 109            | Some timeouts at high load |
| CSHARP  | 338,356 req/s   | c=400               | 0              | Best overall - zero timeouts |
| NGINX   | 9,164 req/s     | c=25                | 0              | Load balancing overhead |

### Order Endpoints - Peak Performance

| Service | Peak Throughput | Optimal Concurrency | Total Timeouts | Notes |
|---------|-----------------|---------------------|----------------|-------|
| PYTHON  | 360.7 req/s     | c=10                | 866            | Critical issues at high concurrency |
| JAVA    | 427.4 req/s     | c=50                | 45             | Stable across concurrency levels |
| CSHARP  | 1,802.0 req/s   | c=10                | 0              | 5x faster than Java, zero errors |
| NGINX   | 753.4 req/s     | c=25                | 142            | Better than Python direct |

## Key Findings

### Performance Analysis

1. **C# Dominance:**
   - Health endpoints: 21.5x faster than Python, 2.6x faster than Java
   - Order endpoints: 5.0x faster than Java, 5.0x faster than Python
   - Zero timeouts across all concurrency levels
   - Best production choice for maximum performance

2. **Python Critical Issues:**
   - Health endpoints perform well at low concurrency (15,728 req/s at c=10)
   - Order endpoints have severe problems: 866 timeouts at c=300
   - NOT production-ready for write-heavy workloads
   - Database connection pool exhaustion suspected

3. **Java Stability:**
   - Consistent performance across concurrency levels
   - Order endpoints: 413-427 req/s (variance <4%)
   - Best choice for predictable, stable throughput
   - Some timeouts (109 at c=800 health, 45 at c=300 orders)

4. **Nginx Load Balancing:**
   - Health endpoints: 9,164 req/s (lower than direct C# access)
   - Order endpoints: 753 req/s (2.1x better than direct Python)
   - Provides high availability but adds latency overhead
   - Good choice when distributing load across multiple backends

### Production Recommendations

**For Maximum Performance:**
- Use C# service directly (1,802 req/s orders, 338,356 req/s health)
- Optimal concurrency: c=10 for orders, c=400 for health

**For High Availability:**
- Use Nginx load balancer (753 req/s orders, 9,164 req/s health)
- Distributes load across all backend services
- Provides failover capability

**Do NOT Use:**
- Python service for production order processing (critical timeout issues)

## Comparison to Goals

**Original Goal:** 100,000 order requests within 1 second, zero 503 errors, no oversale

**Current State:**
- C# peak: 1,802 orders/second (55x below goal)
- Nginx peak: 753 orders/second (133x below goal)
- Zero 503 errors achieved at optimal concurrency
- No oversale issues observed

**Gap Analysis:**
- Need 55x performance improvement to reach goal with C#
- Requires architectural changes: caching, connection pooling optimization, query optimization
- Consider horizontal scaling with multiple C# instances behind Nginx

## File Locations

### Raw Data
- `raw/full_data.csv` - Complete benchmark results (all tests)
- `raw/health_summary.csv` - Health endpoint summary
- `raw/order_summary.csv` - Order endpoint summary
- `raw/peak_performance.csv` - Peak performance by service
- `raw/archive_early_tests/` - Earlier test runs

### Reports
- `reports/performance_summary.md` - Formatted tables and charts guidance
- `reports/summary.md` - Detailed analysis report
- `reports/summary_20260102_*.md` - Historical summary snapshots

### Visualizations
- `visualizations/` - (Empty - ready for future chart generation)

## Reproducing This Campaign

```bash
# 1. Ensure services are running
docker compose up -d
sleep 30
bash scripts/verification/SACRED_VERIFICATION.sh

# 2. Run fixed sweep tests
source lib/fixed_sweep.sh

# Test each service
for service in python java csharp nginx; do
  case $service in
    python) port=8000 ;;
    java) port=8081 ;;
    csharp) port=8082 ;;
    nginx) port=443 ;;
  esac

  # Health endpoint
  run_fixed_sweep "variant_y" "$service" "$port" "/health" "health" \
    "benchmark_results/campaigns/$(date +%Y%m%d)_reproduction/raw/${service}_health.csv"

  # Order endpoint
  run_fixed_sweep "variant_y" "$service" "$port" "/api/v1/orders" "order" \
    "benchmark_results/campaigns/$(date +%Y%m%d)_reproduction/raw/${service}_orders.csv"
done

# 3. Generate reports
bash tools/generate_summary_reports.sh \
  benchmark_results/campaigns/$(date +%Y%m%d)_reproduction/raw/*.csv \
  > benchmark_results/campaigns/$(date +%Y%m%d)_reproduction/reports/summary.md
```

## Next Steps

1. **Investigate Python timeout issues**
   - Profile database connection pool
   - Check async I/O bottlenecks
   - Review FastAPI configuration

2. **Optimize C# for flash sale goal**
   - Implement connection pooling optimization
   - Add Redis caching for campaign status
   - Profile query performance

3. **Test horizontal scaling**
   - Deploy multiple C# instances
   - Measure Nginx load balancing at scale
   - Determine optimal instance count

4. **Create variant comparison**
   - Compare Variant Y vs Variant X (with Redis)
   - Analyze performance differences
   - Document trade-offs

---

**Campaign Created By:** Syracuse
**Test Execution Date:** 2026-01-02
**Repository:** /home/syracuse/flashsale
