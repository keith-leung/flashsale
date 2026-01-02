# Variant Y Enhancement - Execution Plan Summary

**Date:** 2026-01-02
**Status:** Ready for Execution
**Estimated Time:** 8-10 hours

---

## ✅ Corrections Applied

### 1. Complete Performance Table with Nginx
**Fixed:** Added Nginx round-robin results to performance table

**Table Now Includes:**
- Individual Services: C#, Java, Python (/health + /orders)
- **Nginx Round-Robin**: /health + /orders (ADDED)
- Full metrics: Throughput, Latency (Avg/P95/P99), Error Rate
- Peak/Plateau detection for each service

**Key Insight:** Nginx /orders constrained by Python (slowest service at 272 req/s)

### 2. Correct Test Execution Order
**Fixed:** Tests now run in strict order per your specification

**Mandatory Order:**
```
Step 0: Python Internal Unit Tests (29 tests)
   ↓
Step 1: Health Benchmarks - Individual Services
   C# → Java → Python (fastest to slowest)
   ↓
Step 2: Nginx /health (Round-Robin)
   ↓
Step 3: Order Benchmarks - Individual Services
   C# → Java → Python (fastest to slowest)
   ↓
Step 4: Nginx /orders (Round-Robin)
```

**Rationale:**
- Unit tests verify correctness FIRST
- Fast services (C#) detect issues before slow services (Python)
- Individual services before load balancer (isolate problems)
- Health endpoints before order endpoints (simple → complex)

---

## 📋 Complete Implementation Plan

### Phase 1: Redis Removal (2 hours)
**Objective:** Physically remove Redis from Variant Y (pure database only)

**Actions:**
1. Remove Redis env vars from docker-compose.yml:
   - `REDIS_URL` (Python)
   - `SPRING_DATA_REDIS_HOST` (Java)
   - `ConnectionStrings__Redis` (C#)

2. Clean Python code:
   - Remove Redis imports
   - Remove `redis` from requirements.txt
   - Delete Redis cache initialization

3. Clean Java code:
   - Remove `spring-boot-starter-data-redis` from pom.xml
   - Delete RedisTemplate beans
   - Remove @Cacheable annotations

4. Clean C# code:
   - **DELETE** `csharp-service/Services/RedisCacheService.cs`
   - Remove StackExchange.Redis from .csproj
   - Remove Redis service registration from Program.cs

5. Verify:
   - Rebuild all services
   - No Redis connections in logs
   - SACRED_VERIFICATION passes

### Phase 2: Inventory Scaling (30 minutes)
**Objective:** Support large-scale testing (60K+ orders in 30s)

**Actions:**
```sql
-- Scale inventory to 1 million units
UPDATE inventory
SET available_quantity = 1000000,
    reserved_quantity = 0,
    fulfilled_quantity = 0;

-- Scale flash sale campaign to 500K
UPDATE flash_sale_campaigns
SET total_sale_limit = 500000,
    sold_quantity = 0
WHERE spu_id = '550e8400-e29b-41d4-a716-446655440001';
```

**Rationale:**
- 30s test @ 2000 req/s = 60,000 orders
- 10x safety margin = 600,000 capacity
- Inventory: 1M, Campaign: 500K

### Phase 3: Peak/Plateau Testing (4 hours)
**Objective:** Find optimal concurrency for each service

**Concurrency Sweeps:**
| Service | Endpoint | Concurrency Levels | Expected Peak |
|---------|----------|-------------------|---------------|
| C# | /health | 100, 200, 400, 600, 800 | ~600 |
| Java | /health | 50, 100, 200, 300, 400 | ~200 |
| Python | /health | 25, 50, 100, 150, 200 | ~100 |
| Nginx | /health | 10, 25, 50 | ~25 |
| C# | /orders | 10, 25, 50, 75 | ~25-50 |
| Java | /orders | 25, 50, 75, 100 | ~75 |
| Python | /orders | 10, 25, 50, 75 | ~50 |
| Nginx | /orders | 25, 50, 75 | ~50 |

**Plateau Detection:**
```
Peak = Highest throughput achieved
Plateau = Throughput increase <5% despite 50%+ more connections
Degradation = Throughput decrease >5% (overload)
```

### Phase 4: Enhanced SACRED_VERIFICATION.sh (2 hours)
**Objective:** Automated plateau testing with mandatory execution order

**Features:**
- Concurrency sweeps for all services
- Automatic peak detection
- CSV export: `results.csv`
- Full metrics: throughput, latency (avg/p95/p99), errors
- Enforces mandatory test order (stops on failure)

**Usage:**
```bash
bash SACRED_VERIFICATION.sh   # Always runs 30s per test (full mode only)
```

**No quick mode** - All tests run for 30 seconds to ensure thorough and reproducible results.

### Phase 5: Performance Table (1 hour)
**Objective:** Single source of truth for performance data

**Table Schema:**
```
Variant | Service | Endpoint | Concurrency | Duration | Throughput | Avg Latency | P95 | P99 | Error% | Notes
```

**Features:**
- Auto-generated from results.csv
- Replaces messy README.md presentation
- Supports multi-variant comparison (Y vs X)
- Markdown format for easy viewing

**Output:** `PERFORMANCE_RESULTS.md`

### Phase 6: Documentation (1 hour)
**Objective:** Update all documentation

**Files to Update:**
1. `README.md` - Replace performance section with table reference
2. `CONVENTIONS.md` - Update Policy 4 with new parameters
3. `PERFORMANCE_RESULTS.md` - Generated table (NEW)

---

## 🎯 Success Criteria

### Redis Removal
- [ ] No Redis imports in any service code
- [ ] No Redis dependencies in package files
- [ ] Services start without Redis connection
- [ ] All 29 unit tests pass
- [ ] Dual scenario test passes

### Plateau Testing
- [ ] Peak detected for each service/endpoint
- [ ] Plateau confirmed (stable or degrading throughput)
- [ ] Full latency distribution recorded
- [ ] CSV results exported
- [ ] Zero manual intervention needed

### Performance Table
- [ ] All services included (C#, Java, Python, Nginx)
- [ ] All endpoints covered (/health, /orders)
- [ ] Concurrency sweeps documented
- [ ] Peak/plateau clearly marked
- [ ] Future variant comparison supported

---

## 📊 Expected Final Table (Preview)

```
HEALTH ENDPOINTS - Individual Services
├─ C# /health: PEAK @ -c600 (439,128 req/s)
├─ Java /health: PEAK @ -c200 (191,432 req/s)
└─ Python /health: PEAK @ -c100 (41,234 req/s)

HEALTH ENDPOINT - Nginx Round-Robin
└─ Nginx /health: PEAK @ -c25 (8,310 req/s)

ORDER ENDPOINTS - Individual Services
├─ C# /orders: PEAK @ -c25 (2,134 req/s)
├─ Java /orders: PEAK @ -c75 (1,587 req/s)
└─ Python /orders: PEAK @ -c50 (272 req/s)

ORDER ENDPOINT - Nginx Round-Robin
└─ Nginx /orders: PEAK @ -c50 (694 req/s) - Constrained by Python
```

---

## ⚠️ Risk Mitigation

1. **Inventory Exhaustion**
   - Solution: 1M units, reset between runs
   - Monitor: `SELECT SUM(available_quantity) FROM inventory`

2. **Database Connection Limits**
   - Solution: Adjust `max_connections` in MariaDB
   - Monitor: `SHOW PROCESSLIST` during tests

3. **Redis Removal Breaking Code**
   - Solution: Incremental removal, test after each service
   - Rollback: Git commit before each phase

4. **Test Duration**
   - Fixed: 30s per test (full mode only)
   - Total time: ~5-10 minutes per complete run
   - Parallel execution NOT used (sequential for isolation)

---

## 🚀 Execution Sequence

1. **Backup** (5 min)
   ```bash
   git commit -am "Pre-Redis-removal backup"
   mysqldump -u syracuse -p orange315 > backup_$(date +%Y%m%d).sql
   ```

2. **Redis Removal** (2 hours)
   - Clean Python → Rebuild → Test
   - Clean Java → Rebuild → Test
   - Clean C# → Rebuild → Test
   - Run SACRED_VERIFICATION

3. **Inventory Scaling** (30 min)
   - Update inventory SQL
   - Update campaign SQL
   - Verify capacity

4. **Plateau Testing** (4 hours)
   - Implement script enhancements
   - Test on each service
   - Validate plateau detection

5. **Table Generation** (1 hour)
   - Create CSV parser
   - Generate markdown table
   - Verify formatting

6. **Documentation** (1 hour)
   - Update README.md
   - Create PERFORMANCE_RESULTS.md
   - Update CONVENTIONS.md

---

## ✅ Ready to Execute

**Full plan documented in:** `/home/syracuse/flashsale/VARIANT_Y_ENHANCEMENT_PLAN.md`

**Awaiting user approval to begin Phase 1: Redis Removal**
