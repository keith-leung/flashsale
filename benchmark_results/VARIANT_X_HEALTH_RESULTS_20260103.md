# Variant X Health Endpoint Benchmark Results
**Date:** 2026-01-03
**Test Type:** Adaptive Plateau Detection
**Endpoints Tested:** Health endpoints only (order endpoints pending schema fix)

## Test Configuration
- Services: Python (30011), Java (8016), C# (30012), Nginx (8445)
- Method: Adaptive plateau detection
- Base Duration: 10s per test
- Network: 10.89.0.0/24 (Variant X dedicated network)

## Health Endpoint Results - Sustained Plateau Performance

| Service | **Plateau Throughput** | Optimal Config | Avg Latency | p99 Latency |
|---------|------------------------|----------------|-------------|-------------|
| **C#**     | **383,343 req/s** | t=24 c=1536 | 4.25ms | 10.72ms |
| **JAVA**   | **194,087 req/s** | t=24 c=2000 | 10.79ms | 17.82ms |
| **PYTHON** | **19,032 req/s**  | t=15 c=115  | 6.90ms | 37.78ms |
| **NGINX**  | **12,005 req/s**  | t=19 c=390  | 29.06ms | 36.61ms |

## Comparison with Variant Y Health Benchmarks

| Service | Variant X (Redis) | Variant Y (DB) | Difference |
|---------|-------------------|----------------|------------|
| **C#**     | 383,343 req/s | 378,580 req/s | **+1.3%** ✅ |
| **JAVA**   | 194,087 req/s | 183,361 req/s | **+5.8%** ✅ |
| **PYTHON** | 19,032 req/s  | 31,368 req/s  | **-39.3%** ⚠️ |
| **NGINX**  | 12,005 req/s  | 11,380 req/s  | **+5.5%** ✅ |

## Key Findings

### ✅ Strengths
1. **C# Performance:** Slightly faster than Variant Y (+1.3%)
2. **Java Performance:** Noticeable improvement (+5.8%)
3. **Nginx Performance:** Better load balancing (+5.5%)

### ⚠️ Issues Identified
1. **Python Performance:** 39% slower than Variant Y
   - Variant X: 19K req/s vs Variant Y: 31K req/s
   - Needs investigation (possible Redis connection overhead?)

2. **Order Endpoints:** Not benchmarked due to schema issues:
   - Database has `flash_sale_id` column
   - SACRED schema requires `flash_sale_campaign_id`
   - Python model relationship error: `NoForeignKeysError`

3. **Nginx Configuration:** Fixed during testing
   - Was using Variant Y IPs (10.88.0.x)
   - Updated to Variant X IPs (10.89.0.x)

## Next Steps

1. **Investigate Python Performance:** Why is health endpoint 39% slower?
2. **Fix Order Schema:** Update database column name to match SACRED
3. **Run Order Benchmarks:** Once schema is fixed, test `/api/v1/orders` endpoint
4. **Full Comparison:** Compare order performance (the critical metric)

## Raw Data
- CSV File: `benchmark_results/variant_X_health_raw_20260103_043740.csv`
- Format: Compatible with Variant Y CSV schema
- Total Tests: 47 adaptive iterations across 4 services

---

**Test Completed:** 2026-01-03 04:37 UTC  
**Tested By:** Claude (Automated Adaptive Benchmarking)  
**Status:** ⚠️ PARTIAL - Health endpoints tested, order endpoints pending schema fix
