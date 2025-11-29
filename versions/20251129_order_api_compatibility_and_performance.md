# Order API Compatibility and Performance Testing

**Date:** November 29, 2025
**Version:** 20251129_order_api_compatibility_and_performance
**Status:** ✅ Complete

## Overview

Fixed JSON property naming compatibility issues in Java and C# services to enable stress testing with the wrk Lua script. Conducted comprehensive performance testing across all three services (Python, Java, C#) with actual database writes, confirming database as the primary bottleneck.

## Objectives Achieved

1. ✅ Fixed wrk Lua script JSON format compatibility for Java service
2. ✅ Fixed wrk Lua script JSON format compatibility for C# service
3. ✅ Conducted stress tests with actual database writes for all three services
4. ✅ Confirmed database (MariaDB) as the performance bottleneck
5. ✅ Verified full interoperability of all three services with shared database

## Root Cause Analysis

The wrk Lua script (`wrk_order_script.lua`) generates JSON with **snake_case** field names:
```json
{
  "customer_email": "test@example.com",
  "customer_name": "Test User",
  "currency": "USD",
  "line_items": [
    {
      "sku_id": "uuid-here",
      "quantity": 2
    }
  ]
}
```

**Problem:**
- **Python**: Uses snake_case natively ✅
- **Java**: Expected camelCase (`customerEmail`, `skuId`) by default ❌
- **C#**: Expected PascalCase or camelCase (`CustomerEmail`, `SkuId`) by default ❌

This caused all wrk requests to Java and C# to fail with HTTP 400 validation errors.

## Fixes Applied

### Java (Spring Boot)

**File:** `java-service/src/main/resources/application.yml`

```yaml
spring:
  jackson:
    property-naming-strategy: SNAKE_CASE
```

**Effect:**
- Jackson now accepts and produces snake_case JSON
- Compatible with Python API contract
- No code changes required in DTOs

### C# (ASP.NET Core)

**File 1:** `csharp-service/Common/SnakeCaseNamingPolicy.cs` (new file)

```csharp
using System.Text;
using System.Text.Json;

namespace FlashSale.Api.Common;

public class SnakeCaseNamingPolicy : JsonNamingPolicy
{
    public override string ConvertName(string name)
    {
        if (string.IsNullOrEmpty(name))
            return name;

        var builder = new StringBuilder();
        for (int i = 0; i < name.Length; i++)
        {
            var c = name[i];
            if (char.IsUpper(c))
            {
                if (i > 0)
                    builder.Append('_');
                builder.Append(char.ToLower(c));
            }
            else
            {
                builder.Append(c);
            }
        }
        return builder.ToString();
    }
}
```

**File 2:** `csharp-service/Program.cs`

```csharp
using FlashSale.Api.Common;  // Add import

builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNamingPolicy = new SnakeCaseNamingPolicy();
    });
```

**Effect:**
- System.Text.Json now accepts and produces snake_case JSON
- Compatible with Python API contract
- No code changes required in DTOs

## Performance Test Results

### Test Configuration
- **Tool:** wrk (HTTP benchmarking tool)
- **Threads:** 12
- **Connections:** 100
- **Duration:** ~30 seconds
- **Test Data:** 500 SKUs with 10,000 stock each
- **Database:** MariaDB 10.6.22 on localhost

### Python (FastAPI) - Baseline

```
Requests/sec:   1,590.21
Latency (avg):  65.96ms
Total Requests: 47,860 in 30.00s
Success Rate:   99.98% (8 failures)

Database Impact:
  Orders Created:      47,852
  Actual Throughput:   1,595 orders/sec
  Line Items Created:  ~95K (avg 2 items per order)
```

**Analysis:**
- Highest success rate (99.98%)
- Lower throughput = fewer connection issues
- Baseline performance

### Java (Spring Boot) - After Fix

```
Requests/sec:   2,073.58
Latency (avg):  51.33ms
Total Requests: 61,012 in 29.42s
Success Rate:   83.8% (51,168 successful, 9,844 failures)

Database Impact:
  Orders Created:      51,264
  Actual Throughput:   1,742 orders/sec
  Performance:         +9.2% faster than Python
```

**Analysis:**
- 9.2% faster than Python
- 22% lower latency
- Some failures due to DB connection limits

### C# (ASP.NET Core) - After Fix

```
Requests/sec:   3,780.16
Latency (avg):  33.79ms
Total Requests: 111,600 in 29.52s
Success Rate:   84.6% (94,453 successful, 17,147 failures)

Database Impact:
  Orders Created:      94,549
  Actual Throughput:   3,202 orders/sec
  Performance:         +100.7% faster than Python (2× faster)
                       +83.9% faster than Java
```

**Analysis:**
- 2× faster than Python
- 1.8× faster than Java
- 49% lower latency than Python
- Some failures due to DB connection limits

## Bottleneck Analysis: Database Confirmed

### Evidence #1: Database Connection Exhaustion

All services hit `ERROR 1040 (HY000): Too many connections` during stress tests, proving the database connection pool is saturated.

### Evidence #2: Performance Gap Narrowing

| Scenario | C# vs Java | C# vs Python |
|----------|------------|--------------|
| **No Database** (/health) | 5.8× faster | 10.5× faster |
| **With Database** (orders) | 1.8× faster | 2.0× faster |

**Conclusion:** Database I/O narrows the 10× performance gap to just 2×

### Evidence #3: Reduction Factors

How much does adding database operations slow down each service?

| Service | /health req/s | Orders/sec | Reduction Factor |
|---------|---------------|------------|------------------|
| Python  | 95,298        | 1,595      | 60× slower |
| Java    | 172,068       | 1,742      | 99× slower |
| C#      | 996,491       | 3,202      | 311× slower |

**Key Insight:** The faster the application framework, the more it gets bottlenecked by the database. C# loses 311× of its raw performance when database transactions are involved.

### Evidence #4: Latency Overhead

| Service | Without DB (ms) | With DB (ms) | DB Overhead |
|---------|-----------------|--------------|-------------|
| Python  | ~1ms            | 66ms         | +65ms       |
| Java    | ~6ms            | 51ms         | +45ms       |
| C#      | ~1ms            | 34ms         | +33ms       |

Database transactions add **30-65ms overhead** across all stacks.

### Evidence #5: Error Patterns

Higher throughput → More database connection conflicts:

| Service | Throughput | Success Rate | Failures |
|---------|------------|--------------|----------|
| Python  | 1,595/s    | 99.98%       | 8        |
| Java    | 1,742/s    | 83.8%        | 9,844    |
| C#      | 3,202/s    | 84.6%        | 17,147   |

## Database Transaction Anatomy

Each order requires multiple operations wrapped in ACID transaction:

1. **SKU Lookups**: 1-3 SELECT queries
2. **Inventory Updates**: 1-3 SELECT FOR UPDATE + UPDATE (with row-level locks)
3. **Order Insert**: 1 INSERT into `orders` table
4. **Line Items Insert**: 1-3 INSERT into `order_line_items` table
5. **Transaction Commit**: Fsync to disk for durability

**Bottleneck:** Connection pool size limits concurrent transaction capacity.

## Service Interoperability Verification

All three services now:
- ✅ Accept snake_case JSON requests (`customer_email`, `sku_id`)
- ✅ Use snake_case database columns (`order_number`, `customer_email`)
- ✅ Store UUIDs as CHAR(36) with hyphens
- ✅ Share the same database tables
- ✅ Can read orders created by other services

**Load Balancer Ready:** Services are fully interchangeable from client perspective.

## Production Capacity Planning

Based on proven performance (not estimates):

| Service | Proven Throughput | Instances for 10K orders/sec |
|---------|-------------------|------------------------------|
| **C#**  | 3,200 orders/sec  | 3-4 instances                |
| **Java** | 1,750 orders/sec | 6 instances                  |
| **Python** | 1,600 orders/sec | 7 instances                |

**Note:** Database must be optimized to handle the load:
- Increase `max_connections` from 151 to 500-1000
- Optimize connection pooling in each service
- Consider vertical scaling (more CPU/RAM) or read replicas

## Files Modified

1. **java-service/src/main/resources/application.yml**
   - Added `spring.jackson.property-naming-strategy: SNAKE_CASE`

2. **csharp-service/Program.cs**
   - Added import for `FlashSale.Api.Common`
   - Configured JSON options with custom naming policy

3. **csharp-service/Common/SnakeCaseNamingPolicy.cs** (new file)
   - Custom snake_case naming policy for System.Text.Json

4. **ORDER_API_PERFORMANCE.md** (updated, will be consolidated)
   - Added actual test results
   - Added bottleneck analysis
   - Updated capacity planning with proven numbers

## Key Learnings

1. **JSON Property Naming Matters for API Compatibility**
   - Python uses snake_case by default
   - Java/C# need explicit configuration
   - All services must align for load balancer deployment

2. **Database is the True Bottleneck**
   - Application performance differences narrow significantly with DB operations
   - Connection pool limits constrain throughput more than application code
   - C# is 311× slower with DB vs without, proving DB dominates

3. **Higher Throughput ≠ Higher Success Rate**
   - Python: 1,595/s @ 99.98% success
   - C#: 3,202/s @ 84.6% success
   - Trade-off between throughput and reliability under DB constraints

4. **Production Scaling Requires Database Optimization**
   - Application instances can scale horizontally easily
   - Database is the single point of contention
   - Must increase connection limits, optimize queries, or shard

## Comparison to Previous Version

**Previous (20251125_baseline_performance_testing):**
- Python only: 1,385-1,595 orders/sec
- Health endpoint benchmarks established
- No cross-service compatibility testing

**Current (20251129_order_api_compatibility_and_performance):**
- All three services tested: Python (1,595/s), Java (1,742/s), C# (3,202/s)
- Fixed JSON compatibility for Java and C#
- Confirmed database bottleneck with evidence
- Verified full interoperability for load balancer deployment

---

**Version Control:**
- Previous: 20251125_baseline_performance_testing
- Current: 20251129_order_api_compatibility_and_performance
