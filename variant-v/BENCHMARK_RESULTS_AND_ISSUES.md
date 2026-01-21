# Variant V - Benchmark Results & Critical Issues

**Date:** 2026-01-20  
**Status:** ⚠️ BENCHMARK COMPLETE - CRITICAL DATA INTEGRITY ISSUES FOUND

---

## Benchmark Results Summary

### Performance Improvements Achieved

| Service | Before Fix | After Fix | Improvement | Latency |
|---------|------------|-----------|-------------|---------|
| **Python** | 42,058 req/s | 39,226 req/s | -6.8% | 1.65ms |
| **Java** | 1,212 req/s | 30,438 req/s | **+2,411%** ✅ | 6.16ms |
| **C#** | 1,728 req/s | 7,432 req/s | **+330%** ✅ | 5.37ms |

**Verdict**: Java improved 25x, but C# still underperforming. Python remains fastest.

---

## Critical Data Integrity Issue: OVERSALE

### The Problem

**Audit Log shows:** 6,390 confirmed orders  
**Redis shows:** 166 total sold (campaign limit)  
**OVERSALE:** 6,390 - 166 = **6,224 orders oversold** ❌

### Root Cause: Race Condition in Java & C#

**Current Broken Flow (Java & C#):**
```
Thread 1 → Check limit (OK) → Create audit → Acquire lock → GET counter (50) → SET counter (51) → Confirm audit
Thread 2 → Check limit (OK) → Create audit → Acquire lock → GET counter (51) → SET counter (52) → Confirm audit
Thread 3 → Check limit (OK) → Create audit → Acquire lock → GET counter (52) → SET counter (53) → Confirm audit
...
Thread 166 → Check limit (OK) → Create audit → Acquire lock → GET counter (165) → SET counter (166) → Confirm audit
Thread 167 → Check limit (OK) → Create audit → Acquire lock → GET counter (166) → SET counter (166) → ❌ Still confirms audit!
Thread 168 → Check limit (OK) → Create audit → Acquire lock → GET counter (166) → SET counter (166) → ❌ Still confirms audit!
```

**What's Happening:**
1. Multiple threads pass validation (all see counter < limit)
2. They all create audits and acquire locks
3. They SET the counter (which doesn't change if already at limit)
4. They ALL confirm their audits regardless of whether counter actually incremented

### Why Python Works Correctly

**Python Implementation:**
```python
# Python uses atomic INCRBY which returns the new value
total_sold = redis_node.incrby(total_sold_key, quantity)  # Returns NEW value after increment

if total_sold > total_limit:  # Check AFTER increment
    # Fail audit - counter exceeded limit
    await audit_service.fail_audit(audit_id, "Campaign limit exceeded")
    return False
```

**Java & C# Problem:**
```java
// Java/C# do GET then SET (not atomic)
Long totalSold = Long.parseLong(redis.get(campaignKey));  // Read
Long newTotalSold = totalSold + quantity;                 // Calculate
redis.set(campaignKey, newTotalSold.toString());          // Write - no verification!
// No check if increment actually succeeded!
```

---

## The Fix Required

### Solution: Atomic Counter Operations

Use Redis `INCRBY` which returns the NEW value after increment, allowing validation:

**Correct Pattern:**
```java
// Step 1: Increment and get NEW value
Long newTotalSold = redisClient.getAtomicLong(campaignKey).addAndGet(quantity);

// Step 2: Check if increment exceeded limit
if (newTotalSold > totalLimit) {
    // Step 3: Decrement to rollback (restore original state)
    redisClient.getAtomicLong(campaignKey).addAndGet(-quantity);
    
    // Step 4: Fail audit and return 409
    auditService.failAudit(audit.getId(), "Campaign limit exceeded");
    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
}
```

This ensures:
- Only one thread can increment at a time (atomic operation)
- We check if the increment exceeded the limit
- If exceeded, we rollback and reject the order
- No overselling possible

### Code Changes Needed

**Java - OrderController.java:**
```java
// REPLACING:
Long totalSold = ...;
Long newTotalSold = totalSold + request.getQuantity();
redissonClient.getBucket(campaignKey).set(newTotalSold.toString());

// WITH:
RLongAtomicLong counter = redissonClient.getAtomicLong(campaignKey);
Long newTotalSold = counter.addAndGet(request.getQuantity());

if (newTotalSold > totalLimit) {
    // Rollback
    counter.addAndGet(-request.getQuantity());
    auditService.failAudit(audit.getId(), "Campaign limit exceeded");
    response.setStatus("FAILED");
    response.setMessage("Campaign sold out");
    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
}
```

**C# - OrdersController.cs:**
```csharp
// REPLACING:
await db.StringSetAsync(campaignKey, (totalSold ?? 0) + request.Quantity);

// WITH:
long newTotalSold = (long)await db.StringIncrementAsync(campaignKey, request.Quantity);

if (totalLimit.HasValue && newTotalSold > totalLimit.Value)
{
    // Rollback
    await db.StringDecrementAsync(campaignKey, request.Quantity);
    await _auditService.FailAuditAsync(audit.Id, "Campaign limit exceeded");
    response.Status = "FAILED";
    response.Message = "Campaign sold out";
    return Conflict(response);
}
```

---

## Summary of Issues Found

### ✅ FIXED: Performance Issues
1. **Java improved 25x** (1,212 → 30,438 req/s) - Still slower than Python though
2. **C# improved 4x** (1,728 → 7,432 req/s) - Still much slower than Python
3. **Root cause**: Blocking database operations (JPA/EF Core) vs Python async

### ❌ BROKEN: Data Integrity
1. **Campaign limits not enforced** → Overselling by 6,224 orders
2. **Race condition in GET-SET pattern** → Multiple threads bypass limit
3. **Need atomic INCRBY operations** → Currently reading then writing

### ❌ BROKEN: Failed Records
1. **218,883 FAILED audits** (should be 409 Conflict)
2. **Happens because**: Orders that lost the race get marked FAILED
3. **Should be**: Return 409 Conflict without creating audit

---

## Required Before Re-Testing

### Critical Fixes (Must Have)

- [ ] **Java**: Use RLongAtomicLong.addAndGet() instead of GET+SET
- [ ] **C#**: Use StringIncrementAsync() instead of StringGetAsync+StringSetAsync
- [ ] **Both**: Check increment result vs limit, rollback if exceeded
- [ ] **Both**: Only confirm audit if increment succeeded within limit
- [ ] **Both**: Return 409 Conflict for expected rejections (no audit)

### Performance Optimizations (Should Have)

- [ ] **Java**: Investigate why still 30% slower than Python
  - Profile blocking in JPA/Hibernate
  - Consider HikariCP pool tuning
  - Check Redisson configuration
  
- [ ] **C#**: Investigate why 80% slower than Python
  - Profile EF Core operations
  - Consider Dapper instead of EF Core
  - Check StackExchange.Redis configuration

### Validation (Must Pass)

After fixes, these must be true:

```sql
SELECT status, COUNT(*) FROM audit_order_log GROUP BY status;

-- Must show:
-- confirmed: 166 (exactly campaign limit)
-- failed: 0 (zero failed records)
-- pending: 0 (zero pending records)
```

```bash
redis-cli GET campaign:test-flash-campaign-001:total_sold
# Must be: 166

redis-cli GET campaign:test-flash-campaign-001:sku:xxx:remaining
# Must be: 0
```

---

## Why Python Outperforms Java/C#

The session context mentions "the same design should properly make C# and Java outperform python".

**But the designs are NOT the same:**

| Aspect | Python | Java | C# |
|--------|--------|------|----|
| **Database Driver** | aiomysql (async) | JDBC (blocking) | ADO.NET (mixed) |
| **ORM** | Raw SQL + async | JPA/Hibernate (blocking) | EF Core (mixed) |
| **Redis Client** | redis-py (async) | Redisson (sync ops) | StackExchange.Redis (async) |
| **Lock Style** | async/await | try-with-resources | await using |
| **Thread Model** | Event loop | Thread pool | Thread pool |

**Python advantages:**
1. True async throughout (no blocking I/O)
2. Event loop handles 1000s connections per thread
3. Non-blocking database and Redis calls

**Java/C# disadvantages:**
1. Synchronous database calls block threads
2. Thread pool limits concurrent requests
3. Blocking calls waste CPU cycles

**To match Python performance, Java/C# need:**
- Java: Spring WebFlux + R2DBC (reactive) instead of Spring MVC + JPA
- C#: Minimal APIs + Dapper async fully instead of EF Core

---

## Next Steps Priority

### 1. Fix Oversale (Critical)
Implement atomic counter operations in Java and C# with rollback on limit exceeded.

### 2. Verify Zero Failed Records
Ensure proper 409 Conflict responses for expected rejections.

### 3. Performance Optimization
Profile and optimize database connection usage in Java/C#.

### 4. Re-run Benchmarks
Validate with zero oversale and zero failed records.

---

**Document Author:** Kimi K2 Thinking  
**Status:** Critical data integrity issue blocking qualification  
**Priority:** Fix oversale immediately before any further benchmarking
