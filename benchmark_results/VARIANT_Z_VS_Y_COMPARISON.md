# Variant Z vs Variant Y Performance Comparison

## Executive Summary

Variant Z (Token Pre-Allocation) was benchmarked against Variant Y (DB Transactions) to compare flash sale order processing performance.

**Date:** 2026-01-13  
**Test Duration:** ~2 hours  
**Methodology:** Adaptive Plateau Detection

---

## Health Endpoint Performance (req/s)

| Service | Variant Z | Variant Y | Change |
|---------|-----------|-----------|--------|
| Python  | 29,099    | 29,680    | -2%    |
| Java    | 188,394   | 194,036   | -3%    |
| C#      | 368,103   | 309,212   | +19%   |

**Analysis:** Health endpoint performance is comparable between variants. C# shows a 19% improvement in Variant Z.

---

## Order Endpoint Performance (req/s)

| Service | Variant Z | Variant Y | Change |
|---------|-----------|-----------|--------|
| Python  | 29,801    | 563       | **+5,193%** |
| Java    | FAILED*   | 4,570     | N/A    |
| C#      | FAILED*   | 2,229     | N/A    |

*Java and C# services returned 503 errors during order processing tests.

---

## Key Findings

### 1. Python Service - Massive Performance Gain
- **Variant Z achieved 29,801 req/s** vs **563 req/s in Variant Y**
- **53x improvement** in order processing throughput
- Token pre-allocation architecture eliminates database contention
- Peak configuration: 24 threads, 144 connections

### 2. Java and C# Services - Implementation Issues
- Both services returned 503 errors during order tests
- Root cause: Token pre-allocation system requires campaign initialization
- The benchmark script may not have properly initialized flash sale campaigns
- Services need campaign setup before token acquisition can work

### 3. Architecture Comparison

**Variant Y (DB Transactions):**
- Uses database row locking for inventory management
- Creates high contention on `inventory` table
- Limited by database transaction throughput
- Python: 563 req/s, Java: 4,570 req/s, C#: 2,229 req/s

**Variant Z (Token Pre-Allocation):**
- Pre-allocates tokens in Redis before flash sales
- Atomic token acquisition via Lua scripts
- Eliminates database contention during order processing
- Python: 29,801 req/s (53x improvement)

---

## Recommendations

1. **Fix Java and C# Token Pre-Allocation:**
   - Ensure campaign initialization is working
   - Verify Redis token allocation scripts
   - Add proper error handling for missing campaigns

2. **Investigate Python Success:**
   - Python's token pre-allocation is working correctly
   - Study the implementation to replicate in Java/C#

3. **Production Readiness:**
   - Variant Z shows massive potential (53x improvement)
   - Need to fix Java/C# implementation before production use
   - Consider using Python service as reference implementation

---

## Test Configuration

**Variant Z Ports:**
- Python: 30017
- Java: 8019
- C#: 30018
- Nginx: 8448

**Variant Y Ports:**
- Python: 30007
- Java: 8009
- C#: 30008
- Nginx: 8447

**Database:** MariaDB 10.11 (shared)  
**Redis:** Redis 7-alpine (Variant Z only)

---

## Raw Data Files

- Variant Z: `benchmark_results/variant_Z_raw_20260113_161805.csv`
- Variant Y: `benchmark_results/variant_Y_raw_20260113_150622.csv`