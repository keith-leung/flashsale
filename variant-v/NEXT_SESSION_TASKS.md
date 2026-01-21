# Variant V - Next Session Tasks Checklist

**Date:** 2026-01-20  
**Status:** CRITICAL ISSUES IDENTIFIED - REQUIRES FIXES BEFORE QUALIFICATION

---

## 🚨 CRITICAL BLOCKERS - Must Fix Before Re-Testing

### 1. Data Integrity: Oversale Bug (HIGHEST PRIORITY)

**Problem:** Campaign limit is 166 units, but audit log shows 6,390 confirmed orders
- **Oversale:** 6,390 - 166 = **6,224 orders oversold** ❌
- **Impact:** System cannot guarantee zero oversale - **blocking qualification**

**Root Cause:** Race condition in Java/C# counter operations
- Use GET then SET (non-atomic) instead of atomic INCRBY
- Multiple threads pass validation simultaneously
- All create audits and confirm, even though counter only increments to 166

**Fix Required:**
- Use atomic INCRBY/StringIncrementAsync (returns new value)
- Check if increment exceeded limit, rollback if needed
- Only confirm audit if increment succeeded within limit

**Files to Modify:**
- `java-service/src/main/java/com/flashsale/controller/OrderController.java` - Lines 78-86
- `csharp-service/Controllers/OrdersController.cs` - Lines 77-79

---

### 2. Failed Records: Should be 409 Conflict (HIGH PRIORITY)

**Problem:** 218,883 audit records marked "failed" instead of proper 409 Conflict
- **Impact:** Audit log pollution, incorrect error tracking

**Root Cause:** Exception handlers mark audits as FAILED for expected rejections
- Early validation should return 409 BEFORE creating audit
- Only unexpected exceptions should mark as FAILED

**Fix Required:**
- Move campaign/sku validation BEFORE audit creation
- Return 409 Conflict response without creating audit for expected rejections
- Only create audit and mark FAILED for unexpected errors

**Files to Modify:**
- `java-service/src/main/java/com/flashsale/controller/OrderController.java` - Lines 35-50
- `csharp-service/Controllers/OrdersController.cs` - Lines 34-49

---

## 📊 PERFORMANCE INVESTIGATION (MEDIUM PRIORITY)

### 3. Java Performance: 30,438 req/s (25x improvement, but still 25% slower than Python)

**Problem:** Java should be faster than Python (compiled vs interpreted)

**Root Cause Analysis:**
- Python: Fully async (aiomysql + aioredis) - non-blocking I/O
- Java: Blocking JPA/Hibernate database operations
- Java: Synchronous Redisson Redis operations (GET, SET not async)

**Investigation Required:**
- [ ] Profile database operations with JPA/Hibernate
- [ ] Check Redisson async API usage (using sync methods)
- [ ] Analyze thread pool saturation under load
- [ ] Profile lock acquisition latency

**Potential Fixes:**
- **Quick fix:** Tune HikariCP connection pool (max pool size, timeouts)
- **Medium fix:** Use Redisson async API with CompletableFuture
- **Best fix:** Migrate to Spring WebFlux + R2DBC (reactive database)

---

### 4. C# Performance: 7,432 req/s (4x improvement, but 80% slower than Python)

**Problem:** C# should be much faster than both Java and Python

**Root Cause Analysis:**
- C#: Mix of async and blocking operations
- EF Core async operations may still block at driver level
- Default connection string may not enable async pipeline

**Investigation Required:**
- [ ] Profile EF Core SaveChangesAsync (is it truly async?)
- [ ] Check StackExchange.Redis async implementation
- [ ] Analyze connection pool usage and exhaustion
- [ ] Profile lock acquisition latency

**Potential Fixes:**
- **Quick fix:** Replace EF Core with Dapper (lightweight, faster)
- **Medium fix:** Tune connection string: `async=true;Connection Lifetime=0;`
- **Best fix:** Replace EF Core with raw async ADO.NET commands

---

## ✅ VALIDATION CHECKLIST (After Fixes)

### Pre-Test Setup
- [ ] Rebuild all three services with atomic counter fixes
- [ ] Reset Redis campaign: total_sold=0, total_limit=1000, sku_remaining=166
- [ ] Truncate audit_order_log table (start fresh)

### Single-Request Validation
- [ ] Send ONE order request to each service
- [ ] Verify HTTP 201 Created response
- [ ] Verify audit log shows 1 confirmed record
- [ ] Verify Redis total_sold=1, sku_remaining=165
- [ ] Verify no FAILED or PENDING records

### Load Test Sequence

**Phase 1: Low Concurrency (10 connections)**
- [ ] Run wrk: `wrk -t4 -c10 -d30s` for all 3 services
- [ ] Verify confirmed orders ≈ 30 (campaign not exhausted)
- [ ] Verify Redis total_sold matches confirmed count
- [ ] Verify 0 FAILED, 0 PENDING records

**Phase 2: Campaign Limit Test (50 connections)**
- [ ] Run wrk: `wrk -t8 -c50 -d30s` for all 3 services
- [ ] Verify EXACTLY 166 confirmed orders (campaign limit)
- [ ] Verify remaining requests return HTTP 409
- [ ] Verify NO FAILED records (0 failures)
- [ ] Verify Redis total_sold=166, sku_remaining=0

**Phase 3: Performance Benchmark (actual throughput)**
- [ ] Configure realistic campaign: 50,000 units
- [ ] Run wrk with adaptive plateau detection
- [ ] Measure peak throughput for each service
- [ ] Verify zero oversale throughout test

### Post-Benchmark Validation (Critical)

**⚠️ THESE MUST PASS FOR QUALIFICATION:**

```sql
-- Query 1: Verify zero oversized
SELECT 
    status, 
    COUNT(*) as count
FROM audit_order_log 
WHERE flash_sale_campaign_id = 'test-flash-campaign-001'
GROUP BY status;

-- Expected Result:
-- | status    | count |
-- |-----------|-------|
-- | confirmed | 166   |
-- | failed    | 0     |
-- | pending   | 0     |
```

```sql
-- Query 2: Verify Redis counters match audit
-- (Get audit count)
SELECT COUNT(*) FROM audit_order_log 
WHERE status = 'confirmed';

-- (Should match Redis GET campaign:xxx:total_sold)
-- Must be: 166 = 166
```

```bash
# Query 3: Verify no failed records
SELECT COUNT(*) FROM audit_order_log WHERE status = 'failed';
# Must be: 0

SELECT COUNT(*) FROM audit_order_log WHERE status = 'pending';
# Must be: 0
```

```bash
# Query 4: Verify campaign enforcement
redis-cli GET campaign:test-flash-campaign-001:total_sold
# Must be: 166

redis-cli GET campaign:test-flash-campaign-001:sku:xxx:remaining
# Must be: 0
```

---

## 🎯 SUCCESS CRITERIA (Must All Pass)

### Data Integrity (Non-Negotiable)
- [ ] **Zero oversale**: Confirmed orders ≤ Campaign limit (166)
- [ ] **Zero failed records**: No audits marked FAILED for expected rejections
- [ ] **Zero pending records**: All audits reach final state (confirmed or cleaned up)
- [ ] **Redis-audit consistency**: Redis counters match confirmed audit count

### Performance Targets
- [ ] **Python**: Maintain 35,000+ req/s (async baseline)
- [ ] **Java**: Achieve 50,000+ req/s (should beat Python with reactive stack)
- [ ] **C#**: Achieve 60,000+ req/s (should beat both with optimized code)

### Error Handling
- [ ] All 409 Conflict responses have no audit record created
- [ ] All 500 errors properly mark audit as FAILED
- [ ] Lock timeouts return 409, not 500
- [ ] Campaign sold out returns 409, not FAILED

---

## 📝 TEST DOCUMENTATION REQUIRED

### After Fixes Are Applied

**1. Summary Report (`BENCHMARK_FINAL_RESULTS.md`)**
- [ ] Performance numbers for all 3 services
- [ ] Data integrity verification (screenshots of queries)
- [ ] Race condition fix explanation
- [ ] Failed records elimination verification

**2. Race Condition Fix Documentation (`RACE_CONDITION_FIX.md`)**
- [ ] Problem description (before fix)
- [ ] Solution explanation (atomic operations)
- [ ] Code snippets showing INCRBY usage
- [ ] Verification test results

**3. Performance Analysis (`PERFORMANCE_ANALYSIS.md`)**
- [ ] Why Python is fastest (async throughout)
- [ ] Why Java is slower (blocking database ops)
- [ ] Why C# is slowest (EF Core overhead)
- [ ] Recommendations for achieving parity

**4. Qualification Decision Document (`QUALIFICATION_DECISION.md`)**
- [ ] Summary of all issues found and fixed
- [ ] Data integrity verification (pass/fail)
- [ ] Performance comparison table
- [ ] Final verdict: Can Variant V qualify?

---

## 🔧 TECHNICAL DETAILS FOR FIXES

### Java Redis Atomic Counter

**Current (Broken):**
```java
String totalSoldStr = (String) redissonClient.getBucket(campaignKey).get();
Long totalSold = Long.parseLong(totalSoldStr);
Long newTotalSold = totalSold + quantity;
redissonClient.getBucket(campaignKey).set(newTotalSold.toString());
```

**Fixed (Atomic with Rollback):**
```java
// Early check before audit creation
RLongAtomicLong counter = redissonClient.getAtomicLong(campaignKey);
Long current = counter.get();
if (current >= totalLimit) {
    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
}

// After audit creation, atomic increment
Long newTotalSold = counter.addAndGet(quantity);

// Verify increment didn't exceed limit
if (newTotalSold > totalLimit) {
    // Rollback: restore counter to previous value
    counter.addAndGet(-quantity);
    
    // Fail audit and return conflict
    auditService.failAudit(audit.getId(), "Campaign limit exceeded");
    response.setStatus("FAILED");
    response.setMessage("Campaign sold out");
    return ResponseEntity.status(HttpStatus.CONFLICT).body(response);
}

// Success: confirm audit
auditService.confirmAudit(audit.getId());
```

### C# Redis Atomic Counter

**Current (Broken):**
```csharp
var totalSold = (long?)await db.StringGetAsync(campaignKey);
await db.StringSetAsync(campaignKey, (totalSold ?? 0) + request.Quantity);
```

**Fixed (Atomic with Rollback):**
```csharp
// Early check before audit creation
var current = (long?)await db.StringGetAsync(campaignKey);
if (current >= totalLimit) {
    return Conflict(response);
}

// After audit creation, atomic increment
long newTotalSold = (long)await db.StringIncrementAsync(campaignKey, request.Quantity);

// Verify increment didn't exceed limit
if (totalLimit.HasValue && newTotalSold > totalLimit.Value) {
    // Rollback: restore counter to previous value
    await db.StringDecrementAsync(campaignKey, request.Quantity);
    
    // Fail audit and return conflict
    await _auditService.FailAuditAsync(audit.Id, "Campaign limit exceeded");
    response.Status = "FAILED";
    response.Message = "Campaign sold out";
    return Conflict(response);
}

// Success: confirm audit
await _auditService.ConfirmAuditAsync(audit.Id);
```

---

## 🚨 CURRENT STATUS: CANNOT QUALIFY

⚠️ **Variant V is NOT ready for qualification** due to:

1. ⚠️ Critical: **6,224 orders oversold** (data integrity violation)
2. ⚠️ Critical: **218,883 FAILED records** (should be 0)
3. ⚠️ Performance: **C# is 80% slower than Python** (should be faster)
4. ⚠️ Performance: **Java is 25% slower than Python** (should be faster)

### Required to Qualify

**Must Fix:**
- [ ] Zero oversale (atomic counter operations with rollback)
- [ ] Zero failed records (early validation, 409 before audit creation)

**Should Fix:**
- [ ] Java performance parity (reactive database access)
- [ ] C# performance parity (replace EF Core with Dapper)

**Once fixed, Variant V can qualify.**

---

**Document Author:** Kimi K2 Thinking  
**Status:** Critical fixes needed - Re-test required  
**Next Session:** Fix atomic counters and performance bottlenecks
