# Variant A Benchmark Analysis Report (Final)
**Date:** 2026-01-31
**Test Environment:** Local Podman containers (variant-a network)

## Executive Summary

| Service | Small Biz Peak | Big Biz Peak | Optimal Use Case |
|---------|----------------|--------------|------------------|
| **C#**    | 5,181 RPS      | **99,908 RPS** | High-volume flash sales |
| **Java**  | 1,926 RPS      | 1,999 RPS    | Consistent performance |
| **Python**| 605 RPS        | 619 RPS      | Small-scale operations |
| **Nginx** | 4,685 RPS      | 1,394 RPS    | Load balancing |

## Scenario Definitions

### Small Business (5K items)
- **Campaign:** 00000001-0000-0000-0000-000000000001
- **Total Inventory:** 5,000 items
- **Pre-allocation:** 100% (no Redis refills)
- **Allocation:** C# 34%, Java 33%, Python 33%
- **Watermark:** 0% (disabled)
- **Use Case:** Quick flash sales that sell out fast

### Big Business (1M items)
- **Campaign:** 00000002-0000-0000-0000-000000000001
- **Total Inventory:** 1,000,000 items
- **Pre-allocation:** 10% (90% in Redis for refills)
- **Allocation:** C# 34%, Java 33%, Python 33%
- **Watermark:** 30% (trigger refill at 30% remaining)
- **Use Case:** Sustained high-volume flash sales

## Detailed Results

### C# Service Performance

| Scenario | Concurrency | RPS | Latency (avg) | Latency (max) |
|----------|-------------|-----|---------------|---------------|
| Small Biz | c=10 | 4,809 | 2.12ms | 102.90ms |
| Small Biz | c=100 | 5,007 | 19.10ms | 43.88ms |
| Small Biz | **c=200** | **5,181** | 38.49ms | 135.38ms |
| Big Biz | c=50 | 71,515 | 0.86ms | 35.49ms |
| Big Biz | c=150 | 89,491 | 5.41ms | 90.22ms |
| Big Biz | **c=300** | **99,908** | 8.47ms | 145.85ms |

**Analysis:**
- **Small Biz:** Limited by small inventory pool (1,700 items/C#). RPS capped by inventory turnover.
- **Big Biz:** Scales to ~100k RPS with ample inventory (34,000 initial + refills).
- **Key Insight:** C# performance is inventory-bound, not CPU-bound.

### Java Service Performance

| Scenario | Concurrency | RPS | Latency (avg) | Latency (max) |
|----------|-------------|-----|---------------|---------------|
| Small Biz | **c=100** | **1,926** | 51.61ms | 170.24ms |
| Big Biz | c=100 | 1,955 | 50.78ms | 153.66ms |
| Big Biz | **c=300** | **1,999** | 148.01ms | 554.02ms |

**Analysis:**
- Consistent ~2k RPS regardless of inventory size
- Virtual Threads (Project Loom) handle concurrency well
- Bottleneck likely in GC or connection pooling

### Python Service Performance

| Scenario | Concurrency | RPS | Latency (avg) | Latency (max) |
|----------|-------------|-----|---------------|---------------|
| Small Biz | **c=50** | **605** | 79.02ms | 245.97ms |
| Big Biz | **c=25** | **619** | 38.79ms | 249.80ms |

**Analysis:**
- Consistent ~600 RPS regardless of scenario
- GIL contention limits throughput
- Best at low concurrency (c=25-50)

### Nginx Load Balancer Performance

| Scenario | Concurrency | RPS | Latency (avg) | Notes |
|----------|-------------|-----|---------------|-------|
| Small Biz | **c=100** | **4,685** | 24.02ms | Routing to all backends |
| Big Biz | **c=200** | **1,394** | 245.57ms | Slower than expected |

**Analysis:**
- Small Biz: High RPS due to C# handling most requests
- Big Biz: Lower RPS due to Python/Java bottleneck
- Round-robin distributes load evenly, but performance limited by slowest backend

## Little's Law Analysis

For sustainable flash sale at target RPS:

```
Inventory Needed = RPS × Average_Latency × Safety_Factor

Example for C# at 100k RPS:
- Avg Latency: 10ms = 0.01s
- Safety Factor: 2x
- Inventory per second: 100,000 × 0.01 × 2 = 2,000 items/second
- For 10-minute sale: 2,000 × 600 = 1,200,000 items minimum
```

## Refill Mechanism Analysis

### Small Biz (No Refills)
- All inventory pre-allocated to service instances
- No Redis I/O during hot path
- Inventory depletes linearly
- ~5k RPS sustained until sellout

### Big Biz (Continuous Refills)
- 10% initial allocation (34k items for C#)
- Refill triggered at 30% watermark (~10k items remaining)
- Batch size: 10,000 items per refill
- At 100k RPS: ~10 refills/second from Redis

## Recommendations

### For Production Deployment

1. **High-Volume Sales (>50k RPS target):**
   - Use C# as primary backend
   - Configure Big Biz scenario (10% pre-alloc, 30% watermark)
   - Ensure Redis pool has sufficient inventory

2. **Small-Scale Sales (<5k items):**
   - Use 100% pre-allocation to avoid refill overhead
   - Any backend is suitable
   - Consider disabling refill mechanism

3. **Load Balancer Configuration:**
   - Use weighted round-robin: C# 70%, Java 20%, Python 10%
   - Or route all flash sale traffic to C# directly

### Optimal Configurations

| Inventory Size | Recommended Config | Expected Peak |
|----------------|-------------------|---------------|
| <10k items | 100% pre-alloc, no refill | ~5k RPS |
| 10k-100k | 50% pre-alloc, 20% watermark | ~50k RPS |
| 100k-1M | 10% pre-alloc, 30% watermark | ~100k RPS |
| >1M | 5% pre-alloc, 30% watermark | ~127k RPS |

## Raw Data Files

- `variant_a_full_20260131_080023.csv` - Complete benchmark (small_biz + big_biz)
- `variant_a_adaptive_20260130_233531.csv` - Real campaign benchmark
- `variant_a_quick_20260130_230712.csv` - Initial quick benchmark

## Test Campaigns

| Campaign | ID | Items | Pre-alloc | Status |
|----------|-----|-------|-----------|--------|
| Small Biz | 00000001-...-000001 | 5,000 | 100% | active |
| Big Biz | 00000002-...-000001 | 1,000,000 | 10% | active |
| Real Campaign | 99999999-...-333333 | 100,000,000 | 5% | active |

---
*Generated by Variant A Adaptive Benchmark System*
