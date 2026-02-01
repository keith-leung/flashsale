#!/usr/bin/env python3
"""
Complete Variant A Benchmark: Small Business vs Big Business

Scenario A: Small Business (100% RAM)
- Campaign: 00000001-0000-0000-0000-000000000001
- SKU: 00000001-0000-0000-0000-000000000003
- 5M items, 100% preallocated to RAM
- Expected: RPS approaches /health2 (zero Redis I/O)

Scenario B: Big Business (10% RAM + Refill)
- Campaign: aaaaaaaa-bbbb-cccc-dddd-000000000001
- SKU: aaaaaaaa-bbbb-cccc-dddd-000000000003
- 1M items, 10% preallocated (100K), 90% in Redis pool (900K)
- 30% refill watermark (triggers refill at 30K items remaining)
- Expected: Stable RPS if Refill Rate > Consumption Rate
"""

import subprocess
import time
import re
import sys
from datetime import datetime

# Configuration
SMALL_BIZ = {
    "name": "Small Business (100% RAM)",
    "campaign_id": "00000001-0000-0000-0000-000000000001",
    "sku_id": "00000001-0000-0000-0000-000000000003",
    "total": 5000000,
    "prealloc_pct": 100,
    "redis_pct": 0,
}

BIG_BIZ = {
    "name": "Big Business (30% + Refill)",
    "campaign_id": "aaaaaaaa-bbbb-cccc-dddd-000000000001",
    "sku_id": "aaaaaaaa-bbbb-cccc-dddd-000000000003",
    "total": 1000000,
    "prealloc_pct": 30,  # 300K items in RAM (100% to Java)
    "redis_pct": 70,     # 700K items in Redis pool
}

SERVICES = {
    "java": {"port": 8017, "name": "Java", "threads": 4, "container": "flash-java-a"},
    "python": {"port": 30013, "name": "Python", "threads": 4, "container": "flash-python-a"},
    "csharp": {"port": 30014, "name": "C#", "threads": 8, "container": "flash-csharp-a"},
}

CONCURRENCY_LEVELS = [10, 50, 100, 150, 200, 250, 300, 400, 500]
DURATION = 10


def run_cmd(cmd, timeout=60):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except:
        return -1, "", "timeout"


def parse_latency(s):
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


def parse_wrk(output):
    rps = 0.0
    latency_avg = 0.0
    for line in output.split('\n'):
        if 'Requests/sec:' in line:
            match = re.search(r'Requests/sec:\s*([\d.]+)', line)
            if match:
                rps = float(match.group(1))
        elif 'Latency' in line and 'Distribution' not in line:
            parts = line.split()
            if len(parts) >= 2:
                latency_avg = parse_latency(parts[1])
    return rps, latency_avg


def setup_redis_pool(scenario):
    """Set up Redis inventory pool for a scenario."""
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total"]
    redis_pct = scenario["redis_pct"]

    # Calculate Redis pool size
    redis_pool = int(total * redis_pct / 100)

    print(f"  Setting up Redis pool: {redis_pool:,} items ({redis_pct}% of {total:,})")

    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {redis_pool}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {redis_pool}',
    ]

    for cmd in cmds:
        run_cmd(cmd)

    return redis_pool


def reset_redis_full(scenario):
    """Reset Redis to full inventory for repeated testing."""
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total"]

    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {total}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {total}',
    ]

    for cmd in cmds:
        run_cmd(cmd)


def restart_service(service_key):
    svc = SERVICES[service_key]
    print(f"  Restarting {svc['name']}...", end=" ", flush=True)
    run_cmd(f"podman restart {svc['container']}", timeout=30)
    time.sleep(15)

    for _ in range(10):
        rc, stdout, _ = run_cmd(f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{svc['port']}/health", timeout=5)
        if stdout.strip() == "200":
            print("OK")
            return True
        time.sleep(2)
    print("FAILED")
    return False


def create_order_script(sku_id):
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
    path = "/tmp/wrk_order.lua"
    with open(path, "w") as f:
        f.write(script)
    return path


def run_benchmark(service_key, endpoint, concurrency, sku_id=None):
    svc = SERVICES[service_key]
    threads = min(svc["threads"], concurrency)

    if endpoint == "health2":
        url = f"http://localhost:{svc['port']}/health2"
        cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s {url} 2>&1"
    else:
        script = create_order_script(sku_id)
        url = f"http://localhost:{svc['port']}/api/v1/orders"
        cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s -s {script} {url} 2>&1"

    _, stdout, stderr = run_cmd(cmd, timeout=DURATION + 30)
    return parse_wrk(stdout + stderr)


def run_adaptive_benchmark(service_key, scenario, is_health2=False):
    """Run adaptive benchmark to find peak RPS."""
    results = []
    peak_rps = 0
    peak_conc = 0

    print(f"\n  {'Conc':>6} {'RPS':>12} {'Latency':>10}")
    print(f"  {'-'*30}")

    for conc in CONCURRENCY_LEVELS:
        # Reset Redis before each test (for order tests)
        if not is_health2:
            reset_redis_full(scenario)
            time.sleep(0.5)

        # Run benchmark
        if is_health2:
            rps, lat = run_benchmark(service_key, "health2", conc)
        else:
            rps, lat = run_benchmark(service_key, "orders", conc, scenario["sku_id"])

        results.append((conc, rps, lat))

        # Track peak
        if rps > peak_rps:
            peak_rps = rps
            peak_conc = conc

        # Print result
        lat_str = f"{lat:.2f}ms" if lat else "N/A"
        print(f"  {conc:>6} {rps:>12,.0f} {lat_str:>10}")

        # Early stop if performance degrades significantly
        if len(results) >= 3:
            recent = [r[1] for r in results[-3:]]
            if max(recent) < peak_rps * 0.7:
                print(f"  [Performance degraded, stopping early]")
                break

    print(f"  {'-'*30}")
    print(f"  PEAK: {peak_rps:,.0f} RPS @ c={peak_conc}")

    return peak_rps, peak_conc, results


def benchmark_full(service_key):
    """Run complete benchmark for a single service."""
    svc = SERVICES[service_key]
    results = {}

    print("\n" + "=" * 70)
    print(f"BENCHMARKING: {svc['name']}")
    print("=" * 70)

    # Phase 1: /health2 baseline
    print(f"\n[Phase 1] /health2 Baseline")
    setup_redis_pool(SMALL_BIZ)  # Doesn't matter for health2
    if not restart_service(service_key):
        return None

    health2_peak, health2_conc, _ = run_adaptive_benchmark(service_key, SMALL_BIZ, is_health2=True)
    results["health2"] = health2_peak

    # Phase 2: Small Business (100% RAM)
    print(f"\n[Phase 2] Small Business Orders (100% RAM)")
    print(f"  Expected: Should approach /health2 RPS ({health2_peak:,.0f})")
    setup_redis_pool(SMALL_BIZ)
    if not restart_service(service_key):
        return None

    small_peak, small_conc, _ = run_adaptive_benchmark(service_key, SMALL_BIZ)
    results["small_biz"] = small_peak
    small_ratio = (small_peak / health2_peak * 100) if health2_peak > 0 else 0

    # Phase 3: Big Business (10% RAM + Refill)
    print(f"\n[Phase 3] Big Business Orders (10% RAM + Refill)")
    print(f"  Testing refill mechanism under load")
    setup_redis_pool(BIG_BIZ)
    if not restart_service(service_key):
        return None

    big_peak, big_conc, _ = run_adaptive_benchmark(service_key, BIG_BIZ)
    results["big_biz"] = big_peak
    big_ratio = (big_peak / health2_peak * 100) if health2_peak > 0 else 0

    # Summary
    print(f"\n" + "=" * 70)
    print(f"SUMMARY: {svc['name']}")
    print(f"=" * 70)
    print(f"  /health2:          {health2_peak:>12,.0f} RPS (100% baseline)")
    print(f"  Small Biz (100%):  {small_peak:>12,.0f} RPS ({small_ratio:.1f}% of /health2)")
    print(f"  Big Biz (refill):  {big_peak:>12,.0f} RPS ({big_ratio:.1f}% of /health2)")
    print()

    # Analysis
    if small_ratio >= 50:
        print(f"  ✓ Small Business: GOOD - achieving {small_ratio:.0f}% of /health2")
    else:
        print(f"  ⚠ Small Business: DEGRADED - only {small_ratio:.0f}% of /health2")

    refill_efficiency = (big_peak / small_peak * 100) if small_peak > 0 else 0
    if refill_efficiency >= 80:
        print(f"  ✓ Big Business: GOOD - refill mechanism efficient ({refill_efficiency:.0f}% of Small Biz)")
    elif refill_efficiency >= 50:
        print(f"  ⚠ Big Business: ACCEPTABLE - refill adds some overhead ({refill_efficiency:.0f}% of Small Biz)")
    else:
        print(f"  ✗ Big Business: THRASHING - refill bottleneck ({refill_efficiency:.0f}% of Small Biz)")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmark_both_scenarios.py <java|python|csharp|all>")
        sys.exit(1)

    service = sys.argv[1]

    if service == "all":
        all_results = {}
        for svc in ["csharp", "java", "python"]:
            all_results[svc] = benchmark_full(svc)

        print(f"\n" + "=" * 80)
        print("FINAL COMPARISON: All Services")
        print(f"=" * 80)
        print(f"{'Service':<10} {'Health2':>12} {'Small Biz':>12} {'Big Biz':>12} {'SB Ratio':>10} {'BB Ratio':>10}")
        print(f"{'-'*68}")

        for svc, data in all_results.items():
            if data:
                sb_ratio = (data['small_biz'] / data['health2'] * 100) if data['health2'] > 0 else 0
                bb_ratio = (data['big_biz'] / data['health2'] * 100) if data['health2'] > 0 else 0
                print(f"{svc:<10} {data['health2']:>12,.0f} {data['small_biz']:>12,.0f} {data['big_biz']:>12,.0f} {sb_ratio:>9.1f}% {bb_ratio:>9.1f}%")
    else:
        if service not in SERVICES:
            print(f"Unknown service: {service}")
            sys.exit(1)
        benchmark_full(service)


if __name__ == "__main__":
    main()
