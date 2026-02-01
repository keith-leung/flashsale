#!/usr/bin/env python3
"""
Variant A Complete Benchmark: Small Business vs Big Business

Mathematical Foundation:
========================

Scenario A: Small Business (5,000 items)
- 100% preallocated to RAM at startup
- ZERO Redis I/O during benchmark
- Expected: RPS ≈ /health2 RPS (pure in-memory operations)

Scenario B: Big Business (1,000,000 items)
- 10% preallocated (100,000 items initially)
- Refill from Redis when cache < watermark
- Must tune: Refill Rate > Consumption Rate

Refill Math for Scenario B:
- Consumption: Assume 50k RPS (realistic target)
- Redis latency: ~5ms within container network
- Burn in 5ms: 50,000 × 0.005 = 250 items
- Watermark: 30% = 30,000 items (plenty of buffer)
- Chunk size: 10,000 items per refill
- Safe margin: 30,000 - 250 = 29,750 items remaining after refill starts

Usage:
  python benchmark_variant_a_complete.py setup     # Create DB campaigns
  python benchmark_variant_a_complete.py baseline  # Run /health2 baseline
  python benchmark_variant_a_complete.py java      # Test Java service
  python benchmark_variant_a_complete.py python    # Test Python service
  python benchmark_variant_a_complete.py all       # Full benchmark suite
"""

import subprocess
import time
import csv
import os
import re
import sys
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

# ============================================================================
# Configuration
# ============================================================================

# Use the existing large campaign for proper testing
# Campaign 00000001: 5M items * 33% java_allocation = 1.65M items
# This is the "Small Biz Benchmark" campaign with 100% preallocated to RAM
SMALL_BIZ = {
    "campaign_id": "00000001-0000-0000-0000-000000000001",
    "spu_id": "00000001-0000-0000-0000-000000000002",
    "sku_id": "00000001-0000-0000-0000-000000000003",
    "name": "Small Business (100% RAM)",
    "total_inventory": 5000000,  # Java gets 1.65M (33%)
    "preallocate_pct": 100.0,  # 100% in RAM
    "refill_watermark_pct": 0.0,  # No refill needed
    "redis_pct": 0.0,  # Nothing in Redis pool
}

# For Big Business, we need a campaign with partial preallocation
# Using the same campaign but with different Redis pool setup
BIG_BIZ = {
    "campaign_id": "00000001-0000-0000-0000-000000000001",
    "spu_id": "00000001-0000-0000-0000-000000000002",
    "sku_id": "00000001-0000-0000-0000-000000000003",
    "name": "Big Business (with refill)",
    "total_inventory": 5000000,
    "preallocate_pct": 10.0,  # 10% in RAM initially
    "refill_watermark_pct": 30.0,  # Refill when cache < 30%
    "redis_pct": 90.0,  # 90% in Redis pool
}

SERVICES = {
    "java": {
        "port": 8017,
        "name": "Java",
        "threads": 4,
        "container": "flash-java-a",
        "allocation_ratio": 100,  # 100% when testing alone
    },
    "python": {
        "port": 30013,
        "name": "Python",
        "threads": 4,
        "container": "flash-python-a",
        "allocation_ratio": 100,
    },
    "csharp": {
        "port": 30014,
        "name": "C#",
        "threads": 8,
        "container": "flash-csharp-a",
        "allocation_ratio": 100,
    },
}

# Concurrency levels for adaptive search
CONCURRENCY_LEVELS = [10, 25, 50, 100, 150, 200, 250, 300, 400, 500]

# Benchmark duration
DURATION = 10

# Service startup wait
STARTUP_WAIT = 15


@dataclass
class BenchmarkResult:
    timestamp: str
    test_type: str  # "health2" or "orders"
    scenario: str   # "small_biz" or "big_biz"
    service: str
    concurrency: int
    threads: int
    duration: int
    total_requests: int
    rps: float
    latency_avg_ms: float
    latency_max_ms: float
    errors: int
    error_rate: float


def run_cmd(cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def parse_wrk_output(output: str) -> dict:
    """Parse wrk output for metrics."""
    metrics = {
        "rps": 0.0,
        "latency_avg_ms": 0.0,
        "latency_max_ms": 0.0,
        "total_requests": 0,
        "errors": 0,
    }

    for line in output.split('\n'):
        if 'Requests/sec:' in line:
            match = re.search(r'Requests/sec:\s*([\d.]+)', line)
            if match:
                metrics["rps"] = float(match.group(1))
        elif 'Latency' in line and 'Distribution' not in line:
            parts = line.split()
            if len(parts) >= 2:
                metrics["latency_avg_ms"] = parse_latency(parts[1])
            if len(parts) >= 4:
                metrics["latency_max_ms"] = parse_latency(parts[3])
        elif 'requests in' in line:
            match = re.search(r'(\d+)\s+requests', line)
            if match:
                metrics["total_requests"] = int(match.group(1))
        elif 'Non-2xx' in line:
            match = re.search(r'Non-2xx.*?(\d+)', line)
            if match:
                metrics["errors"] = int(match.group(1))

    return metrics


def parse_latency(s: str) -> float:
    """Parse latency string to milliseconds."""
    if not s:
        return 0.0
    try:
        if s.endswith('ms'):
            return float(s[:-2])
        elif s.endswith('s'):
            return float(s[:-1]) * 1000
        elif s.endswith('us'):
            return float(s[:-2]) / 1000
        return float(s)
    except:
        return 0.0


# ============================================================================
# Database Setup
# ============================================================================

def setup_database_campaigns():
    """Create Small Business and Big Business campaigns in the database."""
    print("\n" + "=" * 70)
    print("SETTING UP DATABASE CAMPAIGNS")
    print("=" * 70)

    # SQL to clean and create campaigns
    sql_commands = []

    # Clean existing test data
    sql_commands.append("DELETE FROM flash_sale_campaigns WHERE id IN ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222221');")
    sql_commands.append("DELETE FROM inventory WHERE sku_id IN ('11111111-1111-1111-1111-111111111113', '22222222-2222-2222-2222-222222222223');")
    sql_commands.append("DELETE FROM skus WHERE id IN ('11111111-1111-1111-1111-111111111113', '22222222-2222-2222-2222-222222222223');")
    sql_commands.append("DELETE FROM spus WHERE id IN ('11111111-1111-1111-1111-111111111112', '22222222-2222-2222-2222-222222222222');")

    # Create Small Business campaign
    sql_commands.append(f"""
INSERT INTO spus (id, name, slug, description, is_active, created_at, updated_at)
VALUES ('{SMALL_BIZ["spu_id"]}', 'Small Biz Product', 'small-biz-product', 'Test product', 1, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active, created_at, updated_at)
VALUES ('{SMALL_BIZ["sku_id"]}', 'SMALL-BIZ-001', 'Small Biz SKU', '{SMALL_BIZ["spu_id"]}', 99.99, 50.00, 1.0, 1, 1, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at)
VALUES (UUID(), '{SMALL_BIZ["sku_id"]}', {SMALL_BIZ["total_inventory"]}, 0, 0, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO flash_sale_campaigns (
    id, name, description, spu_id, total_sale_limit, sold_quantity, max_quantity_per_customer,
    flash_price, start_time, end_time, status, is_active,
    preallocate_percentage, redis_percentage, refill_lower_watermark_pct,
    csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
    created_at, updated_at
) VALUES (
    '{SMALL_BIZ["campaign_id"]}', 'Small Business Campaign', 'Test - 100% prealloc',
    '{SMALL_BIZ["spu_id"]}', {SMALL_BIZ["total_inventory"]}, 0, 10,
    79.99, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR), 'active', 1,
    {SMALL_BIZ["preallocate_pct"]}, {SMALL_BIZ["redis_pct"]}, {SMALL_BIZ["refill_watermark_pct"]},
    100, 100, 100,
    NOW(), NOW()
);
""")

    # Create Big Business campaign
    sql_commands.append(f"""
INSERT INTO spus (id, name, slug, description, is_active, created_at, updated_at)
VALUES ('{BIG_BIZ["spu_id"]}', 'Big Biz Product', 'big-biz-product', 'Test product', 1, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO skus (id, sku_code, name, spu_id, price, cost_price, weight, track_inventory, is_active, created_at, updated_at)
VALUES ('{BIG_BIZ["sku_id"]}', 'BIG-BIZ-001', 'Big Biz SKU', '{BIG_BIZ["spu_id"]}', 199.99, 100.00, 2.0, 1, 1, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO inventory (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at)
VALUES (UUID(), '{BIG_BIZ["sku_id"]}', {BIG_BIZ["total_inventory"]}, 0, 0, NOW(), NOW());
""")
    sql_commands.append(f"""
INSERT INTO flash_sale_campaigns (
    id, name, description, spu_id, total_sale_limit, sold_quantity, max_quantity_per_customer,
    flash_price, start_time, end_time, status, is_active,
    preallocate_percentage, redis_percentage, refill_lower_watermark_pct,
    csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
    created_at, updated_at
) VALUES (
    '{BIG_BIZ["campaign_id"]}', 'Big Business Campaign', 'Test - 10% prealloc with refill',
    '{BIG_BIZ["spu_id"]}', {BIG_BIZ["total_inventory"]}, 0, 10,
    149.99, NOW(), DATE_ADD(NOW(), INTERVAL 24 HOUR), 'active', 1,
    {BIG_BIZ["preallocate_pct"]}, {BIG_BIZ["redis_pct"]}, {BIG_BIZ["refill_watermark_pct"]},
    100, 100, 100,
    NOW(), NOW()
);
""")

    # Execute SQL in MariaDB container
    for sql in sql_commands:
        sql_clean = sql.strip().replace('\n', ' ').replace("'", "'\"'\"'")
        cmd = f"podman exec flash-mariadb-a mariadb -uroot -proot orange315 -e '{sql_clean}'"
        rc, stdout, stderr = run_cmd(cmd)
        if rc != 0 and "Duplicate" not in stderr:
            print(f"  SQL Warning: {stderr[:100]}")

    print("  ✓ Created Small Business campaign (5K items, 100% prealloc)")
    print("  ✓ Created Big Business campaign (1M items, 10% prealloc)")

    # Verify campaigns exist
    verify_cmd = "podman exec flash-mariadb-a mariadb -uroot -proot orange315 -e 'SELECT id, name, total_sale_limit, preallocate_percentage FROM flash_sale_campaigns WHERE id IN (\"11111111-1111-1111-1111-111111111111\", \"22222222-2222-2222-2222-222222222221\");'"
    rc, stdout, stderr = run_cmd(verify_cmd)
    print(f"\n  Campaigns in DB:\n{stdout}")

    return True


def setup_redis_pools(scenario: dict):
    """Set up Redis inventory pools for a scenario."""
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total_inventory"]
    redis_pct = scenario["redis_pct"]

    # Calculate Redis pool size
    redis_pool = int(total * redis_pct / 100)

    # For Small Biz (100% prealloc), Redis pool should be 0 initially but we set full for refill safety
    # For Big Biz, Redis pool has 90% of inventory

    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {redis_pool}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {redis_pool}',
    ]

    for cmd in cmds:
        run_cmd(cmd)

    print(f"  Redis pool set: {redis_pool:,} items ({redis_pct}% of {total:,})")


def reset_redis_full(scenario: dict):
    """Reset Redis to FULL inventory (for repeated testing)."""
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total_inventory"]

    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {total}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {total}',
    ]

    for cmd in cmds:
        run_cmd(cmd)


# ============================================================================
# Service Management
# ============================================================================

def restart_service(service_key: str) -> bool:
    """Restart a service and wait for it to be ready."""
    svc = SERVICES[service_key]
    container = svc["container"]
    port = svc["port"]

    print(f"  Restarting {svc['name']}...", end=" ", flush=True)

    rc, _, stderr = run_cmd(f"podman restart {container}", timeout=30)
    if rc != 0:
        print(f"FAILED: {stderr}")
        return False

    time.sleep(STARTUP_WAIT)

    # Verify health
    for _ in range(10):
        rc, stdout, _ = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}/health", timeout=5)
        if stdout.strip() == "200":
            print("OK")
            return True
        time.sleep(2)

    print("TIMEOUT")
    return False


def check_service(service_key: str) -> bool:
    """Check if a service is healthy."""
    svc = SERVICES[service_key]
    rc, stdout, _ = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{svc['port']}/health", timeout=5)
    return stdout.strip() == "200"


# ============================================================================
# Benchmark Functions
# ============================================================================

def run_health2_benchmark(service_key: str, concurrency: int) -> BenchmarkResult:
    """Run /health2 benchmark (pure in-memory, no orders)."""
    svc = SERVICES[service_key]
    threads = min(svc["threads"], concurrency)
    url = f"http://localhost:{svc['port']}/health2"

    cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s {url} 2>&1"
    _, stdout, stderr = run_cmd(cmd, timeout=DURATION + 30)
    output = stdout + stderr

    metrics = parse_wrk_output(output)
    error_rate = (metrics["errors"] / metrics["total_requests"] * 100) if metrics["total_requests"] > 0 else 0

    return BenchmarkResult(
        timestamp=datetime.now().isoformat(),
        test_type="health2",
        scenario="baseline",
        service=service_key,
        concurrency=concurrency,
        threads=threads,
        duration=DURATION,
        total_requests=metrics["total_requests"],
        rps=metrics["rps"],
        latency_avg_ms=metrics["latency_avg_ms"],
        latency_max_ms=metrics["latency_max_ms"],
        errors=metrics["errors"],
        error_rate=error_rate,
    )


def create_order_script(sku_id: str) -> str:
    """Create wrk Lua script for order benchmarking."""
    script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
local counter = 0
request = function()
    counter = counter + 1
    local body = string.format([[{{
        "customer_email": "bench%d@test.com",
        "customer_name": "User %d",
        "line_items": [{{"sku_id": "{sku_id}", "quantity": 1}}],
        "tax_amount": 0, "shipping_amount": 0, "currency": "USD"
    }}]], counter, counter)
    return wrk.format(nil, nil, nil, body)
end
'''
    path = "/tmp/wrk_order_benchmark.lua"
    with open(path, "w") as f:
        f.write(script)
    return path


def run_order_benchmark(service_key: str, scenario: dict, concurrency: int) -> BenchmarkResult:
    """Run order benchmark for a scenario."""
    svc = SERVICES[service_key]
    threads = min(svc["threads"], concurrency)
    script_path = create_order_script(scenario["sku_id"])
    url = f"http://localhost:{svc['port']}/api/v1/orders"

    cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s -s {script_path} {url} 2>&1"
    _, stdout, stderr = run_cmd(cmd, timeout=DURATION + 30)
    output = stdout + stderr

    metrics = parse_wrk_output(output)
    error_rate = (metrics["errors"] / metrics["total_requests"] * 100) if metrics["total_requests"] > 0 else 0

    return BenchmarkResult(
        timestamp=datetime.now().isoformat(),
        test_type="orders",
        scenario=scenario["name"].lower().replace(" ", "_"),
        service=service_key,
        concurrency=concurrency,
        threads=threads,
        duration=DURATION,
        total_requests=metrics["total_requests"],
        rps=metrics["rps"],
        latency_avg_ms=metrics["latency_avg_ms"],
        latency_max_ms=metrics["latency_max_ms"],
        errors=metrics["errors"],
        error_rate=error_rate,
    )


def run_adaptive_benchmark(
    service_key: str,
    test_type: str,  # "health2" or "orders"
    scenario: Optional[dict] = None
) -> List[BenchmarkResult]:
    """Run adaptive benchmark to find peak RPS."""
    results = []
    peak_rps = 0
    peak_conc = 0
    svc = SERVICES[service_key]

    scenario_name = scenario["name"] if scenario else "baseline"
    print(f"\n  {'Conc':>6} {'RPS':>12} {'Lat(avg)':>10} {'Lat(max)':>10} {'Errors':>8}")
    print("  " + "-" * 50)

    for conc in CONCURRENCY_LEVELS:
        # Reset Redis inventory before each test (for orders)
        if test_type == "orders" and scenario:
            reset_redis_full(scenario)
            time.sleep(0.5)

        # Run benchmark
        if test_type == "health2":
            result = run_health2_benchmark(service_key, conc)
        else:
            result = run_order_benchmark(service_key, scenario, conc)

        results.append(result)

        # Track peak
        if result.rps > peak_rps:
            peak_rps = result.rps
            peak_conc = conc

        # Print result
        lat_avg = f"{result.latency_avg_ms:.2f}ms" if result.latency_avg_ms else "N/A"
        lat_max = f"{result.latency_max_ms:.2f}ms" if result.latency_max_ms else "N/A"
        print(f"  {conc:>6} {result.rps:>12,.0f} {lat_avg:>10} {lat_max:>10} {result.errors:>8}")

        # Early stop if performance degrades significantly
        if len(results) >= 3:
            recent = [r.rps for r in results[-3:]]
            if max(recent) < peak_rps * 0.7:
                print(f"  [Performance degraded, stopping early]")
                break

    print("  " + "-" * 50)
    print(f"  PEAK: {peak_rps:,.0f} RPS @ c={peak_conc}")

    return results


# ============================================================================
# Main Benchmark Suite
# ============================================================================

def run_service_benchmark(service_key: str) -> List[BenchmarkResult]:
    """Run complete benchmark for a single service."""
    all_results = []
    svc = SERVICES[service_key]

    print("\n" + "=" * 70)
    print(f"BENCHMARKING: {svc['name']}")
    print("=" * 70)

    # Phase 1: /health2 baseline
    print(f"\n[Phase 1] /health2 Baseline (Pure In-Memory)")
    if not restart_service(service_key):
        print("  FAILED to restart service")
        return all_results

    results = run_adaptive_benchmark(service_key, "health2")
    all_results.extend(results)
    health2_peak = max(r.rps for r in results)

    # Phase 2: Small Business (100% prealloc - should match health2)
    print(f"\n[Phase 2] Small Business Orders (5K items, 100% prealloc)")
    print(f"  Expected: Should approach /health2 RPS ({health2_peak:,.0f})")

    setup_redis_pools(SMALL_BIZ)
    if not restart_service(service_key):
        print("  FAILED to restart service")
        return all_results

    results = run_adaptive_benchmark(service_key, "orders", SMALL_BIZ)
    all_results.extend(results)
    small_biz_peak = max(r.rps for r in results)
    small_ratio = (small_biz_peak / health2_peak * 100) if health2_peak > 0 else 0

    # Phase 3: Big Business (10% prealloc with refill)
    print(f"\n[Phase 3] Big Business Orders (1M items, 10% prealloc + refill)")
    print(f"  Expected: Should maintain stable RPS with refill mechanism")

    setup_redis_pools(BIG_BIZ)
    if not restart_service(service_key):
        print("  FAILED to restart service")
        return all_results

    results = run_adaptive_benchmark(service_key, "orders", BIG_BIZ)
    all_results.extend(results)
    big_biz_peak = max(r.rps for r in results)
    big_ratio = (big_biz_peak / health2_peak * 100) if health2_peak > 0 else 0

    # Summary
    print(f"\n" + "=" * 70)
    print(f"SUMMARY: {svc['name']}")
    print(f"=" * 70)
    print(f"  /health2 Peak:      {health2_peak:>12,.0f} RPS (100% baseline)")
    print(f"  Small Biz Peak:     {small_biz_peak:>12,.0f} RPS ({small_ratio:.1f}% of /health2)")
    print(f"  Big Biz Peak:       {big_biz_peak:>12,.0f} RPS ({big_ratio:.1f}% of /health2)")
    print()

    if small_ratio >= 80:
        print(f"  ✓ Small Business matches /health2 (>80%): Variant A working correctly!")
    else:
        print(f"  ✗ Small Business below target (<80%): Possible bottleneck in order path")

    return all_results


def run_baseline_only(service_key: str) -> List[BenchmarkResult]:
    """Run only /health2 baseline benchmark."""
    all_results = []
    svc = SERVICES[service_key]

    print("\n" + "=" * 70)
    print(f"BASELINE: {svc['name']} /health2")
    print("=" * 70)

    if not restart_service(service_key):
        print("  FAILED to restart service")
        return all_results

    results = run_adaptive_benchmark(service_key, "health2")
    all_results.extend(results)

    peak = max(r.rps for r in results)
    print(f"\n  Peak /health2 RPS: {peak:,.0f}")

    return all_results


def save_results(results: List[BenchmarkResult], suffix: str = ""):
    """Save results to CSV."""
    if not results:
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"/home/syracuse/flashsale/benchmark_results/variant_a_complete_{suffix}_{timestamp}.csv"

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    fieldnames = [
        "timestamp", "test_type", "scenario", "service", "concurrency", "threads",
        "duration", "total_requests", "rps", "latency_avg_ms", "latency_max_ms",
        "errors", "error_rate"
    ]

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nResults saved to: {filename}")
    return filename


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python benchmark_variant_a_complete.py setup     # Create DB campaigns")
        print("  python benchmark_variant_a_complete.py baseline <service>  # /health2 only")
        print("  python benchmark_variant_a_complete.py java      # Full Java benchmark")
        print("  python benchmark_variant_a_complete.py python    # Full Python benchmark")
        print("  python benchmark_variant_a_complete.py csharp    # Full C# benchmark")
        print("  python benchmark_variant_a_complete.py all       # All services")
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup":
        setup_database_campaigns()

    elif command == "baseline":
        service = sys.argv[2] if len(sys.argv) > 2 else "java"
        if service not in SERVICES:
            print(f"Unknown service: {service}")
            sys.exit(1)
        results = run_baseline_only(service)
        save_results(results, f"baseline_{service}")

    elif command in ["java", "python", "csharp"]:
        results = run_service_benchmark(command)
        save_results(results, command)

    elif command == "all":
        all_results = []
        for svc in ["csharp", "java", "python"]:
            results = run_service_benchmark(svc)
            all_results.extend(results)
        save_results(all_results, "all")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
