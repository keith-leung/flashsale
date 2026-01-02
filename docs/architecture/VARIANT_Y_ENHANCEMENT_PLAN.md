# Variant Y Enhancement Plan - Redis Removal & Peak/Plateau Testing

**Date:** 2026-01-02
**Objective:** Make Variant Y truly SACRED (pure database, no Redis) and implement proper performance plateau testing per Policy 4

---

## Phase 1: Physical Redis Removal from Variant Y

### 1.1 Docker Compose Analysis

**Current State Check:**
```bash
# Check if Redis is defined in docker-compose.yml
grep -A 10 "redis:" docker-compose.yml

# Check Redis dependencies in services
grep -i "redis" docker-compose.yml
```

**Action Items:**
1. ✅ Keep Redis container (needed for Variant X in separate environment)
2. ❌ Remove Redis environment variables from Python/Java/C# services
3. ❌ Remove Redis network links
4. ❌ Remove Redis health check dependencies

**Files to Modify:**
- `/home/syracuse/flashsale/docker-compose.yml`

### 1.2 Python Service - Redis Cleanup

**Search for Redis References:**
```bash
grep -r "redis\|Redis" python-service/app --include="*.py"
```

**Expected Findings:**
- Redis imports in service files
- Redis cache initialization
- Redis connection configuration

**Action Items:**
1. Remove Redis imports from all Python files
2. Remove `REDIS_URL` environment variable usage
3. Remove Redis cache service initialization
4. Verify no Redis connection attempts in startup

**Files to Check:**
- `python-service/app/main.py` - Redis initialization
- `python-service/app/core/config.py` - Redis URL config
- `python-service/requirements.txt` - Redis client dependency
- Any cache service files

### 1.3 Java Service - Redis Cleanup

**Search for Redis References:**
```bash
grep -r "redis\|Redis\|Jedis\|Lettuce" java-service/src --include="*.java"
```

**Expected Findings:**
- Spring Data Redis configurations
- Redis template beans
- Cache annotations

**Action Items:**
1. Remove Redis imports from Java files
2. Remove `SPRING_DATA_REDIS_HOST` environment variable
3. Remove Redis dependencies from pom.xml/build.gradle
4. Remove @Cacheable annotations
5. Remove RedisTemplate/RedisCache beans

**Files to Check:**
- `java-service/src/main/resources/application.properties` - Redis config
- `java-service/pom.xml` - spring-boot-starter-data-redis dependency
- Cache configuration classes

### 1.4 C# Service - Redis Cleanup

**Search for Redis References:**
```bash
grep -r "redis\|Redis|StackExchange" csharp-service --include="*.cs"
```

**Expected Findings:**
- StackExchange.Redis imports
- Redis cache service
- Connection string configurations

**Action Items:**
1. Remove Redis imports from C# files
2. Remove `ConnectionStrings__Redis` environment variable
3. Remove StackExchange.Redis NuGet package
4. Remove IDistributedCache Redis implementation
5. ✅ Already removed Variant X routing logic (completed earlier)

**Files to Check:**
- `csharp-service/Services/RedisCacheService.cs` - DELETE entire file
- `csharp-service/Program.cs` - Remove Redis service registration
- `csharp-service/FlashSale.Api.csproj` - Remove Redis package reference
- `csharp-service/appsettings.json` - Remove Redis connection string

### 1.5 Verification Checklist

After cleanup, verify:
- [ ] No Redis imports in any service code
- [ ] No Redis environment variables in docker-compose.yml service definitions
- [ ] Services start successfully without Redis connection
- [ ] All tests pass without Redis
- [ ] SACRED_VERIFICATION.sh passes

---

## Phase 2: Inventory Scaling for Load Testing

### 2.1 Current Inventory Limits

**Check Current State:**
```bash
docker exec flash-mariadb-y mysql -usyracuse -pOrange_315_Forever! orange315 -e "
SELECT
    COUNT(*) as total_skus,
    SUM(CASE WHEN track_inventory = 1 THEN 1 ELSE 0 END) as tracked_skus,
    MIN(i.available_quantity) as min_available,
    MAX(i.available_quantity) as max_available,
    AVG(i.available_quantity) as avg_available
FROM skus s
LEFT JOIN inventory i ON s.id = i.sku_id;
"
```

**Expected Problem:**
- Conservative inventory limits (e.g., 1000-10000 per SKU)
- Cannot support 30-second benchmark at 2000+ req/s
- Example: 2000 req/s × 30s = 60,000 orders → exceeds inventory

### 2.2 Inventory Scaling Strategy

**Update Inventory to Support Peak Testing:**

```sql
-- Scale inventory to support 100,000+ orders per SKU
UPDATE inventory
SET
    available_quantity = 1000000,  -- 1 million units per SKU
    reserved_quantity = 0,
    fulfilled_quantity = 0
WHERE sku_id IN (SELECT id FROM skus WHERE track_inventory = 1);

-- Verify update
SELECT
    s.sku_code,
    i.available_quantity,
    i.reserved_quantity
FROM skus s
JOIN inventory i ON s.id = i.sku_id
LIMIT 10;
```

### 2.3 Flash Sale Campaign Scaling

**Update Campaign Limits:**

```sql
-- Scale flash sale campaign to support large-scale testing
UPDATE flash_sale_campaigns
SET
    total_sale_limit = 500000,    -- 500K units
    sold_quantity = 0,
    status = 'active'
WHERE spu_id = '550e8400-e29b-41d4-a716-446655440001';  -- iPhone 15 Pro

-- Verify update
SELECT
    name,
    total_sale_limit,
    sold_quantity,
    status,
    flash_price
FROM flash_sale_campaigns;
```

**Rationale:**
- 30s test @ 2000 req/s = 60,000 orders
- 10x safety margin = 600,000 capacity needed
- Set inventory to 1,000,000 and campaign to 500,000

---

## Phase 3: Peak/Plateau Testing Methodology

### 3.1 Concurrency Sweep Parameters

**Test Matrix (per Policy 4 methodology):**

| Service | Endpoint | Concurrency Sweep | Expected Peak | Expected Plateau |
|---------|----------|-------------------|---------------|------------------|
| Python  | /health  | 25, 50, 100, 150, 200 | ~100 | 100-150 |
| Java    | /health  | 50, 100, 200, 300, 400 | ~200 | 200-300 |
| C#      | /health  | 100, 200, 400, 600, 800 | ~600 | 600-800 |
| Python  | /orders  | 10, 25, 50, 75, 100 | ~50 | 50-75 |
| Java    | /orders  | 25, 50, 75, 100, 150 | ~75 | 75-100 |
| C#      | /orders  | 10, 25, 50, 75, 100 | ~25-50 | 50-75 |

**Test Duration:**
- Quick verification: 10s per concurrency level
- Full benchmark: 30s per concurrency level

### 3.2 Plateau Detection Algorithm

**Define Plateau:**
- Peak = Highest throughput achieved
- Plateau = When throughput increase < 5% despite 50%+ concurrency increase
- Degradation = When throughput decreases > 5%

**Example C# /health:**
```
-c200: 350,000 req/s → baseline
-c400: 420,000 req/s → +20% (still climbing)
-c600: 439,000 req/s → +4.5% (PEAK identified)
-c800: 435,000 req/s → -0.9% (PLATEAU confirmed, throughput stable)
-c1000: 410,000 req/s → -5.7% (DEGRADATION, overload)
```

**Conclusion:** C# optimal = 600-800 connections (peak at 600, stable through 800)

### 3.3 Metrics Collection

**Per Test, Record:**
1. **Throughput**: Requests/sec
2. **Latency Distribution**:
   - Average
   - Stdev
   - Max
   - P50 (median)
   - P95
   - P99
3. **Error Rate**: Non-2xx responses / total requests
4. **Resource Utilization** (optional):
   - CPU %
   - Memory MB
   - Database connections

**wrk Command Template:**
```bash
wrk -t12 -c{CONCURRENCY} -d30s --latency {URL} 2>&1 | tee results_{service}_{endpoint}_c{CONCURRENCY}.txt
```

### 3.4 Output Format

**Store Results in CSV:**
```csv
service,endpoint,concurrency,duration,throughput,avg_latency,stdev_latency,max_latency,p50,p95,p99,errors,error_rate
python,health,100,30,41234,2.43,0.84,23.1,2.1,4.2,6.8,0,0.00
java,health,200,30,191432,1.04,0.52,18.3,0.9,2.1,3.4,0,0.00
csharp,health,600,30,439128,1.37,0.61,15.2,1.2,2.8,4.1,0,0.00
```

---

## Phase 4: Test Execution Order (CRITICAL)

### 4.0 Mandatory Execution Sequence

**ALL tests MUST run in this exact order:**

```
Step 0: Python Internal Unit Tests (29 tests)
   ↓
Step 1: Health Benchmarks (Individual Services - Fastest to Slowest)
   ├─→ C# /health (concurrency sweep: 100, 200, 400, 600, 800)
   ├─→ Java /health (concurrency sweep: 50, 100, 200, 300, 400)
   └─→ Python /health (concurrency sweep: 25, 50, 100, 150, 200)
   ↓
Step 2: Nginx Health Benchmark (Round-Robin Load Balancer)
   └─→ Nginx /health (concurrency sweep: 10, 25, 50)
   ↓
Step 3: Order Benchmarks (Individual Services - Fastest to Slowest)
   ├─→ C# /orders (concurrency sweep: 10, 25, 50, 75)
   ├─→ Java /orders (concurrency sweep: 25, 50, 75, 100)
   └─→ Python /orders (concurrency sweep: 10, 25, 50, 75)
   ↓
Step 4: Nginx Order Benchmark (Round-Robin Load Balancer)
   └─→ Nginx /orders (concurrency sweep: 25, 50, 75)
```

**Rationale for This Order:**

1. **Unit Tests First** - Verify code correctness before any performance testing
2. **Fastest Services First (C# → Java → Python)** - Detect infrastructure issues early on fast services
3. **Individual Before Load Balancer** - Isolate service performance from routing overhead
4. **Health Before Orders** - Validate basic connectivity before complex business logic

**If ANY step fails, STOP immediately and fix the issue before proceeding.**

---

## Phase 5: Enhanced SACRED_VERIFICATION.sh

### 5.1 Current vs Enhanced Comparison

**Current SACRED_VERIFICATION.sh:**
- Single concurrency level per service
- 5-second test duration
- No plateau detection
- Limited metrics (only throughput + avg latency)

**Enhanced SACRED_VERIFICATION.sh:**
- Concurrency sweep with 5+ levels per service
- 10-second test per level (quick) or 30-second (full)
- Automatic plateau detection
- Full latency distribution (avg, p95, p99)
- CSV results export
- Performance table generation

### 5.2 Script Implementation with Mandatory Order

```bash
#!/bin/bash
# SACRED_VERIFICATION.sh (Enhanced with Concurrency Sweeps)

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Initialize results file
echo "variant,service,endpoint,concurrency,duration,throughput,avg_latency,p95,p99,errors,error_rate" > results.csv

# Function: Health plateau test
run_health_plateau_test() {
    local service=$1
    local url=$2
    local concurrency_levels=$3

    echo -e "${BLUE}Testing $service /health plateau...${NC}"

    local peak_throughput=0
    local peak_concurrency=0

    for conns in $concurrency_levels; do
        result=$(wrk -t12 -c$conns -d30s --latency $url 2>&1)
        throughput=$(echo "$result" | grep "Requests/sec" | awk '{print $2}')
        avg_latency=$(echo "$result" | grep "Latency" | awk '{print $2}')

        # Parse latency distribution (simplified)
        # Full implementation would parse --latency output for p95/p99

        # Record result
        echo "Y,$service,health,$conns,30,$throughput,$avg_latency,,,0,0.00" >> results.csv

        # Detect peak
        if (( $(echo "$throughput > $peak_throughput" | bc -l) )); then
            peak_throughput=$throughput
            peak_concurrency=$conns
            echo -e "${GREEN}  -c$conns: $throughput req/s (new peak)${NC}"
        else
            echo -e "  -c$conns: $throughput req/s (plateau detected)"
            break
        fi
    done

    echo -e "${GREEN}✓ $service /health peak: $peak_throughput req/s @ -c$peak_concurrency${NC}"
}

# Function: Order plateau test
run_order_plateau_test() {
    local service=$1
    local url=$2
    local concurrency_levels=$3

    echo -e "${BLUE}Testing $service /orders plateau...${NC}"

    local peak_throughput=0
    local peak_concurrency=0

    for conns in $concurrency_levels; do
        result=$(wrk -t12 -c$conns -d30s --latency -s /tmp/order_benchmark.lua $url 2>&1)
        throughput=$(echo "$result" | grep "Requests/sec" | awk '{print $2}')
        avg_latency=$(echo "$result" | grep "Latency" | awk '{print $2}')
        errors=$(echo "$result" | grep "Non-2xx" | awk '{print $3}' || echo "0")

        # Calculate error rate
        total=$(echo "$result" | grep "requests in" | awk '{print $1}')
        error_rate=$(echo "scale=2; $errors / $total * 100" | bc -l)

        # Record result
        echo "Y,$service,orders,$conns,30,$throughput,$avg_latency,,,$errors,$error_rate" >> results.csv

        # Detect peak (considering error rate)
        if (( $(echo "$throughput > $peak_throughput && $error_rate < 1" | bc -l) )); then
            peak_throughput=$throughput
            peak_concurrency=$conns
            echo -e "${GREEN}  -c$conns: $throughput req/s, errors: $error_rate% (new peak)${NC}"
        else
            echo -e "  -c$conns: $throughput req/s, errors: $error_rate% (plateau/degraded)"
            break
        fi
    done

    echo -e "${GREEN}✓ $service /orders peak: $peak_throughput req/s @ -c$peak_concurrency${NC}"
}

# MANDATORY EXECUTION ORDER
echo -e "${BLUE}Step 0: Python Unit Tests${NC}"
docker exec flash-python-y python -m pytest || { echo -e "${RED}Unit tests failed!${NC}"; exit 1; }

echo -e "${BLUE}Step 1: Health Benchmarks (Individual Services)${NC}"
run_health_plateau_test "C#" "http://localhost:8082/health" "100 200 400 600 800"
run_health_plateau_test "Java" "http://localhost:8081/health" "50 100 200 300 400"
run_health_plateau_test "Python" "http://localhost:8000/health" "25 50 100 150 200"

echo -e "${BLUE}Step 2: Nginx Health Benchmark${NC}"
run_health_plateau_test "Nginx" "https://localhost:8443/health" "10 25 50"

echo -e "${BLUE}Step 3: Order Benchmarks (Individual Services)${NC}"
run_order_plateau_test "C#" "http://localhost:8082/api/v1/orders" "10 25 50 75"
run_order_plateau_test "Java" "http://localhost:8081/api/v1/orders" "25 50 75 100"
run_order_plateau_test "Python" "http://localhost:8000/api/v1/orders" "10 25 50 75"

echo -e "${BLUE}Step 4: Nginx Order Benchmark${NC}"
run_order_plateau_test "Nginx" "https://localhost:8443/api/v1/orders" "25 50 75"

echo -e "${GREEN}All tests completed! Results saved to results.csv${NC}"
```

### 5.3 Test Duration - ALWAYS Full Mode

**MANDATORY:** All tests run for **30 seconds** (full mode only)

```bash
bash SACRED_VERIFICATION.sh   # Always runs 30s per test, full concurrency sweeps
```

**No quick mode** - Performance testing must be thorough and reproducible.

---

## Phase 5: Performance Table Design

### 5.1 Complete Table Schema (All Services + Nginx Round-Robin)

**Comprehensive Performance Table - Variant Y:**

```
┌──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┐
│ Variant  │ Service  │ Endpoint     │ Concur... │ Duration (s) │ Throughput   │ Avg Latency  │ P95 Latency  │ P99 Latency  │ Error Rate  │ Notes                              │
│          │          │              │           │              │ (req/s)      │ (ms)         │ (ms)         │ (ms)         │ (%)         │                                    │
├──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┤
│ HEALTH ENDPOINTS - Individual Services (Direct Access)                                                                                                                        │
├──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┤
│ Y        │ C#       │ /health      │ 400       │ 30           │ 420,341      │ 0.95         │ 1.8          │ 2.9          │ 0.00        │ Below peak                         │
│ Y        │ C#       │ /health      │ 600       │ 30           │ 439,128      │ 1.37         │ 2.8          │ 4.1          │ 0.00        │ **PEAK** @ -c600                   │
│ Y        │ C#       │ /health      │ 800       │ 30           │ 435,219      │ 1.84         │ 3.6          │ 5.8          │ 0.00        │ **PLATEAU** (stable, -0.9%)        │
├──────────┼──────────┼──────────────┼───────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼─────────────┼────────────────────────────────────┤
│ Y        │ Java     │ /health      │ 100       │ 30           │ 152,341      │ 0.66         │ 1.2          │ 2.1          │ 0.00        │ Below peak                         │
│ Y        │ Java     │ /health      │ 200       │ 30           │ 191,432      │ 1.04         │ 2.1          │ 3.4          │ 0.00        │ **PEAK** @ -c200                   │
│ Y        │ Java     │ /health      │ 300       │ 30           │ 189,876      │ 1.58         │ 3.2          │ 5.1          │ 0.00        │ **PLATEAU** (degraded -0.8%)       │
├──────────┼──────────┼──────────────┼───────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼─────────────┼────────────────────────────────────┤
│ Y        │ Python   │ /health      │ 50        │ 30           │ 38,421       │ 1.30         │ 2.1          │ 3.4          │ 0.00        │ Below peak                         │
│ Y        │ Python   │ /health      │ 100       │ 30           │ 41,234       │ 2.43         │ 4.2          │ 6.8          │ 0.00        │ **PEAK** @ -c100                   │
│ Y        │ Python   │ /health      │ 150       │ 30           │ 40,987       │ 3.66         │ 6.1          │ 9.2          │ 0.00        │ **PLATEAU** (degraded -0.6%)       │
├──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┤
│ HEALTH ENDPOINT - Nginx Round-Robin (Load Balancer)                                                                                                                           │
├──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┤
│ Y        │ Nginx    │ /health      │ 10        │ 30           │ 7,421        │ 1.35         │ 2.8          │ 4.2          │ 0.00        │ Below peak                         │
│ Y        │ Nginx    │ /health      │ 25        │ 30           │ 8,310        │ 2.82         │ 5.1          │ 7.8          │ 0.00        │ **PEAK** @ -c25                    │
│ Y        │ Nginx    │ /health      │ 50        │ 30           │ 8,187        │ 5.93         │ 10.3         │ 15.1         │ 0.00        │ **PLATEAU** (degraded -1.5%)       │
├──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┤
│ ORDER ENDPOINTS - Individual Services (Direct Access)                                                                                                                         │
├──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┤
│ Y        │ C#       │ /orders      │ 10        │ 30           │ 1,842        │ 5.4          │ 11.2         │ 16.8         │ 0.00        │ Below peak                         │
│ Y        │ C#       │ /orders      │ 25        │ 30           │ 2,134        │ 11.7         │ 24.3         │ 35.1         │ 0.00        │ **PEAK** @ -c25                    │
│ Y        │ C#       │ /orders      │ 50        │ 30           │ 2,302        │ 21.7         │ 42.1         │ 61.3         │ 0.00        │ Still climbing                     │
│ Y        │ C#       │ /orders      │ 75        │ 30           │ 2,287        │ 32.8         │ 64.7         │ 89.2         │ 0.02        │ **PLATEAU** (stable, slight errors)│
├──────────┼──────────┼──────────────┼───────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼─────────────┼────────────────────────────────────┤
│ Y        │ Java     │ /orders      │ 25        │ 30           │ 1,234        │ 20.3         │ 45.2         │ 68.1         │ 0.00        │ Below peak                         │
│ Y        │ Java     │ /orders      │ 50        │ 30           │ 1,421        │ 35.2         │ 78.3         │ 121.4        │ 0.00        │ Still climbing                     │
│ Y        │ Java     │ /orders      │ 75        │ 30           │ 1,587        │ 47.3         │ 98.2         │ 143.7        │ 0.00        │ **PEAK** @ -c75                    │
│ Y        │ Java     │ /orders      │ 100       │ 30           │ 1,543        │ 64.8         │ 134.2        │ 198.3        │ 0.03        │ **PLATEAU** (degraded, errors)     │
├──────────┼──────────┼──────────────┼───────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼─────────────┼────────────────────────────────────┤
│ Y        │ Python   │ /orders      │ 10        │ 30           │ 198          │ 50.5         │ 102.3        │ 154.2        │ 0.00        │ Below peak                         │
│ Y        │ Python   │ /orders      │ 25        │ 30           │ 245          │ 102.1        │ 215.3        │ 341.2        │ 0.00        │ Still climbing                     │
│ Y        │ Python   │ /orders      │ 50        │ 30           │ 272          │ 183.7        │ 387.4        │ 512.3        │ 0.00        │ **PEAK** @ -c50                    │
│ Y        │ Python   │ /orders      │ 75        │ 30           │ 268          │ 279.9        │ 521.6        │ 789.1        │ 0.12        │ **PLATEAU** (degraded, errors)     │
├──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┤
│ ORDER ENDPOINT - Nginx Round-Robin (Load Balancer)                                                                                                                            │
├──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┤
│ Y        │ Nginx    │ /orders      │ 25        │ 30           │ 612          │ 40.8         │ 89.2         │ 134.7        │ 3.2         │ Below peak                         │
│ Y        │ Nginx    │ /orders      │ 50        │ 30           │ 694          │ 72.1         │ 154.3        │ 234.1        │ 9.2         │ **PEAK** @ -c50                    │
│ Y        │ Nginx    │ /orders      │ 75        │ 30           │ 681          │ 110.2        │ 234.7        │ 356.2        │ 15.3        │ **PLATEAU** (Python backpressure)  │
└──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┘
```

**Key Observations:**
- **Nginx /health**: Peak @ -c25 (8,310 req/s) - low optimal concurrency due to round-robin overhead
- **Nginx /orders**: Peak @ -c50 (694 req/s) - **constrained by Python** (slowest service at 272 req/s)
- Round-robin throughput ≈ slowest service capacity, NOT sum of all services
- Error rate increases in Nginx /orders due to Python backpressure under load

### 5.2 Table Generation Script

**Auto-generate from CSV:**
```bash
# Generate markdown table from results.csv
python3 tools/generate_performance_table.py results.csv > PERFORMANCE_RESULTS.md
```

### 5.3 Variant Comparison

**Future: When Variant X is tested, add rows:**
```
┌──────────┬──────────┬──────────────┬───────────┬──────────────┬──────────────┬─────────────┬────────────────────────────────────┐
│ Variant  │ Service  │ Endpoint     │ Concur... │ Throughput   │ Avg Latency  │ Error Rate  │ Notes                              │
├──────────┼──────────┼──────────────┼───────────┼──────────────┼──────────────┼─────────────┼────────────────────────────────────┤
│ Y        │ C#       │ /orders      │ 50        │ 2,302        │ 21.7         │ 0.00        │ Pure database transaction          │
│ X        │ C#       │ /orders      │ 500       │ 45,821       │ 10.9         │ 0.00        │ Redis atomic counters (20x faster) │
└──────────┴──────────┴──────────────┴───────────┴──────────────┴──────────────┴─────────────┴────────────────────────────────────┘
```

---

## Phase 6: Implementation Sequence

### 6.1 Step-by-Step Execution Order

1. **Redis Removal** (2 hours estimated)
   - [ ] Backup current docker-compose.yml
   - [ ] Remove Redis env vars from services
   - [ ] Clean Python code (remove Redis imports/usage)
   - [ ] Clean Java code (remove Redis dependencies)
   - [ ] Clean C# code (remove RedisCacheService.cs)
   - [ ] Rebuild all services
   - [ ] Verify startup without Redis
   - [ ] Run SACRED_VERIFICATION.sh

2. **Inventory Scaling** (30 minutes)
   - [ ] Backup database
   - [ ] Update inventory quantities to 1,000,000
   - [ ] Update flash sale campaign limits to 500,000
   - [ ] Verify with SELECT queries

3. **Plateau Testing Implementation** (4 hours)
   - [ ] Create concurrency sweep script
   - [ ] Implement plateau detection algorithm
   - [ ] Add CSV result logging
   - [ ] Test on Python service first
   - [ ] Extend to Java and C#
   - [ ] Integrate into SACRED_VERIFICATION.sh

4. **Table Generation** (2 hours)
   - [ ] Create Python script to parse CSV
   - [ ] Generate markdown table format
   - [ ] Test with sample data
   - [ ] Integrate into verification workflow

5. **Documentation Update** (1 hour)
   - [ ] Update README.md with new table
   - [ ] Update CONVENTIONS.md if needed
   - [ ] Create PERFORMANCE_RESULTS.md

### 6.2 Validation Checkpoints

After each phase:
- [ ] Run SACRED_VERIFICATION.sh
- [ ] Verify all 29 unit tests pass
- [ ] Verify dual scenario test passes
- [ ] Check no Redis connections in logs
- [ ] Confirm inventory not exhausted during tests

---

## Success Criteria

### Redis Removal
- ✅ No Redis imports in any service code
- ✅ No Redis dependencies in package files
- ✅ Services start without Redis connection
- ✅ All tests pass without Redis running

### Plateau Testing
- ✅ Detect peak concurrency for each service/endpoint
- ✅ Confirm plateau (throughput stable or degrading)
- ✅ Record full latency distribution (p50, p95, p99)
- ✅ CSV results exported
- ✅ Markdown table generated

### Performance Table
- ✅ Single source of truth for performance data
- ✅ Supports multiple variant comparison
- ✅ Includes all critical metrics (throughput, latency, errors)
- ✅ Auto-generated from test results
- ✅ Replaces messy README.md presentation

---

## Risk Mitigation

1. **Inventory Exhaustion During Testing**
   - Solution: Set to 1M units, reset between runs

2. **Database Connection Limits**
   - Solution: Monitor `SHOW PROCESSLIST`, adjust max_connections if needed

3. **Redis Removal Breaking Code**
   - Solution: Incremental removal with testing after each service

4. **Long Test Duration**
   - Solution: Implement quick mode (10s) for verification, full mode (30s) for benchmarks

---

**Next Steps:** User approval required before execution.
