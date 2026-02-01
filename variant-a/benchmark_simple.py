#!/usr/bin/env python3
"""
Simple Variant A Benchmark: Compare Orders vs /health2

The key test: With 100% preallocated inventory, order RPS should approach /health2 RPS.
Both operations are pure in-memory with no network I/O.

Campaign: 00000001-0000-0000-0000-000000000001
- 5M items total, 33% to Java = 1.65M items in RAM
- SKU: 00000001-0000-0000-0000-000000000003
"""

import subprocess
import time
import re
import sys
from datetime import datetime

# Configuration
SKU_ID = "00000001-0000-0000-0000-000000000003"
CAMPAIGN_ID = "00000001-0000-0000-0000-000000000001"

SERVICES = {
    "java": {"port": 8017, "name": "Java", "threads": 4, "container": "flash-java-a"},
    "python": {"port": 30013, "name": "Python", "threads": 4, "container": "flash-python-a"},
    "csharp": {"port": 30014, "name": "C#", "threads": 8, "container": "flash-csharp-a"},
}

CONCURRENCY_LEVELS = [10, 50, 100, 150, 200, 250, 300, 400]
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


def reset_redis():
    """Reset Redis inventory to full."""
    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{CAMPAIGN_ID}:redis_pool:spu_counter" 5000000',
        f'podman exec flash-redis-a redis-cli SET "fs:{CAMPAIGN_ID}:redis_pool:sku:{SKU_ID}" 5000000',
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


def create_order_script():
    script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
local counter = 0
request = function()
    counter = counter + 1
    local body = string.format([[{{
        "customer_email": "bench%d@test.com",
        "customer_name": "User %d",
        "line_items": [{{"sku_id": "{SKU_ID}", "quantity": 1}}],
        "tax_amount": 0, "shipping_amount": 0, "currency": "USD"
    }}]], counter, counter)
    return wrk.format(nil, nil, nil, body)
end
'''
    path = "/tmp/wrk_order.lua"
    with open(path, "w") as f:
        f.write(script)
    return path


def run_benchmark(service_key, endpoint, concurrency):
    svc = SERVICES[service_key]
    threads = min(svc["threads"], concurrency)

    if endpoint == "health2":
        url = f"http://localhost:{svc['port']}/health2"
        cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s {url} 2>&1"
    else:
        script = create_order_script()
        url = f"http://localhost:{svc['port']}/api/v1/orders"
        cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s -s {script} {url} 2>&1"

    _, stdout, stderr = run_cmd(cmd, timeout=DURATION + 30)
    return parse_wrk(stdout + stderr)


def benchmark_service(service_key):
    svc = SERVICES[service_key]
    print(f"\n{'='*60}")
    print(f"BENCHMARKING: {svc['name']}")
    print(f"{'='*60}")

    # Phase 1: /health2 baseline
    print(f"\n[1] /health2 Baseline")
    reset_redis()
    if not restart_service(service_key):
        return

    health2_results = []
    print(f"  {'Conc':>6} {'RPS':>12} {'Latency':>10}")
    print(f"  {'-'*30}")

    for conc in CONCURRENCY_LEVELS:
        rps, lat = run_benchmark(service_key, "health2", conc)
        health2_results.append((conc, rps, lat))
        lat_str = f"{lat:.2f}ms" if lat else "N/A"
        print(f"  {conc:>6} {rps:>12,.0f} {lat_str:>10}")

    health2_peak = max(r[1] for r in health2_results)
    health2_best_conc = max(health2_results, key=lambda x: x[1])[0]
    print(f"  PEAK: {health2_peak:,.0f} RPS @ c={health2_best_conc}")

    # Phase 2: Orders (100% prealloc - should match health2)
    print(f"\n[2] Orders (Variant A - 100% RAM)")
    reset_redis()
    if not restart_service(service_key):
        return

    order_results = []
    print(f"  {'Conc':>6} {'RPS':>12} {'Latency':>10}")
    print(f"  {'-'*30}")

    for conc in CONCURRENCY_LEVELS:
        reset_redis()  # Reset before each test
        time.sleep(0.5)
        rps, lat = run_benchmark(service_key, "orders", conc)
        order_results.append((conc, rps, lat))
        lat_str = f"{lat:.2f}ms" if lat else "N/A"
        print(f"  {conc:>6} {rps:>12,.0f} {lat_str:>10}")

    order_peak = max(r[1] for r in order_results)
    order_best_conc = max(order_results, key=lambda x: x[1])[0]
    print(f"  PEAK: {order_peak:,.0f} RPS @ c={order_best_conc}")

    # Summary
    ratio = (order_peak / health2_peak * 100) if health2_peak > 0 else 0
    print(f"\n{'='*60}")
    print(f"SUMMARY: {svc['name']}")
    print(f"{'='*60}")
    print(f"  /health2:  {health2_peak:>12,.0f} RPS (baseline)")
    print(f"  Orders:    {order_peak:>12,.0f} RPS ({ratio:.1f}% of /health2)")

    if ratio >= 50:
        print(f"  ✓ PASS: Order performance is good (>50% of /health2)")
    elif ratio >= 20:
        print(f"  ⚠ WARN: Order performance degraded (20-50% of /health2)")
    else:
        print(f"  ✗ FAIL: Order performance poor (<20% of /health2)")
        print(f"    → Possible causes: SnowflakeIdGenerator lock, Spring overhead, object allocation")

    return {"health2": health2_peak, "orders": order_peak, "ratio": ratio}


def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmark_simple.py <java|python|csharp|all>")
        sys.exit(1)

    service = sys.argv[1]

    if service == "all":
        results = {}
        for svc in ["csharp", "java", "python"]:
            results[svc] = benchmark_service(svc)

        print(f"\n{'='*60}")
        print("FINAL COMPARISON")
        print(f"{'='*60}")
        print(f"{'Service':<10} {'Health2':>12} {'Orders':>12} {'Ratio':>10}")
        print(f"{'-'*46}")
        for svc, data in results.items():
            if data:
                print(f"{svc:<10} {data['health2']:>12,.0f} {data['orders']:>12,.0f} {data['ratio']:>9.1f}%")
    else:
        if service not in SERVICES:
            print(f"Unknown service: {service}")
            sys.exit(1)
        benchmark_service(service)


if __name__ == "__main__":
    main()
