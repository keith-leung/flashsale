#!/usr/bin/env python3
"""
Variant A Adaptive Benchmark V2: Correct Testing Approach

Key improvements:
1. Test each service INDIVIDUALLY with full inventory
2. Restart service before each scenario to reload fresh allocations
3. Reset inventory between EVERY concurrency level
4. Test Nginx separately with ALL services fresh
"""

import subprocess
import time
import csv
import os
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

# ============================================================================
# Configuration
# ============================================================================

SCENARIOS = {
    "small_biz": {
        "campaign_id": "00000001-0000-0000-0000-000000000001",
        "sku_id": "00000001-0000-0000-0000-000000000003",
        "name": "Small Business (5K items)",
        "total_inventory": 5000,
        "prealloc_pct": 100,
    },
    "big_biz": {
        "campaign_id": "00000002-0000-0000-0000-000000000001",
        "sku_id": "00000002-0000-0000-0000-000000000003",
        "name": "Big Business (1M items)",
        "total_inventory": 1000000,
        "prealloc_pct": 10,
    },
}

SERVICES = {
    "csharp": {
        "port": 30014,
        "name": "C#",
        "threads": 8,
        "container": "flash-csharp-a",
    },
    "java": {
        "port": 8017,
        "name": "Java",
        "threads": 4,
        "container": "flash-java-a",
    },
    "python": {
        "port": 30013,
        "name": "Python",
        "threads": 4,
        "container": "flash-python-a",
    },
    "nginx": {
        "port": 8445,
        "name": "Nginx LB",
        "threads": 8,
        "container": "flash-nginx-a",
    },
}

# Adaptive benchmark concurrency levels
CONCURRENCY_LEVELS = [10, 25, 50, 100, 150, 200, 300, 400]

# Benchmark duration per test (seconds)
DURATION = 10

# Wait time after service restart (seconds)
SERVICE_STARTUP_WAIT = 20


@dataclass
class BenchmarkResult:
    timestamp: str
    scenario: str
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


def parse_latency(latency_str: str) -> float:
    """Parse latency string like '1.23ms' or '1.23s' to milliseconds."""
    if not latency_str or latency_str == "N/A":
        return 0.0
    try:
        if latency_str.endswith('ms'):
            return float(latency_str[:-2])
        elif latency_str.endswith('s'):
            return float(latency_str[:-1]) * 1000
        elif latency_str.endswith('us'):
            return float(latency_str[:-2]) / 1000
        return float(latency_str)
    except:
        return 0.0


def reset_redis_inventory(scenario_key: str) -> int:
    """Reset Redis inventory pools to FULL inventory for a scenario."""
    scenario = SCENARIOS[scenario_key]
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total_inventory"]

    # Set FULL inventory in Redis pool (for refills)
    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {total}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {total}',
    ]

    for cmd in cmds:
        subprocess.run(cmd, shell=True, capture_output=True)

    return total


def restart_service(service_key: str) -> bool:
    """Restart a single service and wait for it to be ready."""
    service = SERVICES[service_key]
    container = service["container"]
    port = service["port"]

    print(f"    Restarting {service['name']}...", end=" ", flush=True)

    # Restart container
    result = subprocess.run(
        f"podman restart {container}",
        shell=True, capture_output=True, text=True, timeout=30
    )

    if result.returncode != 0:
        print(f"FAILED: {result.stderr}")
        return False

    # Wait for service to be ready
    time.sleep(SERVICE_STARTUP_WAIT)

    # Verify service is up
    for attempt in range(5):
        try:
            check = subprocess.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{port}/health",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if check.stdout.strip() == "200":
                print("OK")
                return True
        except:
            pass
        time.sleep(2)

    print("TIMEOUT")
    return False


def restart_all_services() -> bool:
    """Restart all backend services for Nginx testing."""
    print("    Restarting all services for Nginx test...")

    # Restart all backend services
    result = subprocess.run(
        "podman restart flash-csharp-a flash-java-a flash-python-a",
        shell=True, capture_output=True, text=True, timeout=60
    )

    # Wait for all services to start (extra time for Python with multiple workers)
    time.sleep(SERVICE_STARTUP_WAIT + 10)

    # Verify all are up
    all_up = True
    for svc_key in ["csharp", "java", "python"]:
        svc = SERVICES[svc_key]
        try:
            check = subprocess.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{svc['port']}/health",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if check.stdout.strip() == "200":
                print(f"      {svc['name']}: OK")
            else:
                print(f"      {svc['name']}: DOWN")
                all_up = False
        except:
            print(f"      {svc['name']}: DOWN")
            all_up = False

    return all_up


def create_wrk_script(sku_id: str) -> str:
    """Create wrk Lua script for benchmarking."""
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
    path = "/tmp/wrk_benchmark_v2.lua"
    with open(path, "w") as f:
        f.write(script)
    return path


def run_single_benchmark(service_key: str, scenario_key: str, concurrency: int) -> BenchmarkResult:
    """Run a single benchmark at specified concurrency."""
    service = SERVICES[service_key]
    scenario = SCENARIOS[scenario_key]

    script_path = create_wrk_script(scenario["sku_id"])
    url = f"http://localhost:{service['port']}/api/v1/orders"
    threads = min(service["threads"], concurrency)

    cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s -s {script_path} {url} 2>&1"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout + result.stderr

    # Parse results
    rps = 0.0
    latency_avg = 0.0
    latency_max = 0.0
    total_requests = 0
    errors = 0

    for line in output.split('\n'):
        if 'Requests/sec:' in line:
            match = re.search(r'Requests/sec:\s*([\d.]+)', line)
            if match:
                rps = float(match.group(1))
        elif 'Latency' in line and 'Distribution' not in line:
            parts = line.split()
            if len(parts) >= 2:
                latency_avg = parse_latency(parts[1])
            if len(parts) >= 4:
                latency_max = parse_latency(parts[3])
        elif 'requests in' in line:
            match = re.search(r'(\d+)\s+requests', line)
            if match:
                total_requests = int(match.group(1))
        elif 'Non-2xx' in line:
            match = re.search(r'Non-2xx.*?(\d+)', line)
            if match:
                errors = int(match.group(1))

    error_rate = (errors / total_requests * 100) if total_requests > 0 else 0

    return BenchmarkResult(
        timestamp=datetime.now().isoformat(),
        scenario=scenario_key,
        service=service_key,
        concurrency=concurrency,
        threads=threads,
        duration=DURATION,
        total_requests=total_requests,
        rps=rps,
        latency_avg_ms=latency_avg,
        latency_max_ms=latency_max,
        errors=errors,
        error_rate=error_rate
    )


def run_adaptive_benchmark_isolated(service_key: str, scenario_key: str) -> List[BenchmarkResult]:
    """
    Run adaptive benchmark for a SINGLE service with proper isolation.
    Resets inventory before EACH concurrency level test.
    """
    results = []
    scenario = SCENARIOS[scenario_key]
    service = SERVICES[service_key]

    print(f"\n{'='*60}")
    print(f"Adaptive Benchmark: {service['name']} / {scenario['name']}")
    print(f"{'='*60}")
    print(f"{'Conc':>6} {'RPS':>12} {'Lat(avg)':>10} {'Lat(max)':>10} {'Errors':>8} {'Err%':>6}")
    print("-" * 60)

    peak_rps = 0
    peak_concurrency = 0

    for conc in CONCURRENCY_LEVELS:
        # CRITICAL: Reset Redis inventory BEFORE each concurrency test
        reset_redis_inventory(scenario_key)
        time.sleep(1)

        result = run_single_benchmark(service_key, scenario_key, conc)
        results.append(result)

        # Track peak
        if result.rps > peak_rps:
            peak_rps = result.rps
            peak_concurrency = conc

        # Print result
        lat_avg = f"{result.latency_avg_ms:.2f}ms" if result.latency_avg_ms else "N/A"
        lat_max = f"{result.latency_max_ms:.2f}ms" if result.latency_max_ms else "N/A"
        print(f"{conc:>6} {result.rps:>12,.0f} {lat_avg:>10} {lat_max:>10} {result.errors:>8} {result.error_rate:>5.1f}%")

        # Early termination if performance degrades significantly
        if len(results) >= 3:
            recent_rps = [r.rps for r in results[-3:]]
            if max(recent_rps) < peak_rps * 0.7:
                print(f"  [Performance degraded, stopping early]")
                break

    print("-" * 60)
    print(f"PEAK: {peak_rps:,.0f} RPS at c={peak_concurrency}")

    return results


def write_csv(results: List[BenchmarkResult], filename: str):
    """Write results to CSV file."""
    fieldnames = [
        "timestamp", "scenario", "service", "concurrency", "threads",
        "duration", "total_requests", "rps", "latency_avg_ms",
        "latency_max_ms", "errors", "error_rate"
    ]

    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nResults saved to: {filename}")


def analyze_results(results: List[BenchmarkResult]):
    """Analyze and print summary."""
    print(f"\n{'='*70}")
    print("BENCHMARK ANALYSIS")
    print(f"{'='*70}\n")

    # Group by service and scenario
    from collections import defaultdict
    grouped = defaultdict(list)

    for r in results:
        key = (r.service, r.scenario)
        grouped[key].append(r)

    # Find peak for each service/scenario
    print(f"{'Service':<10} {'Scenario':<25} {'Peak RPS':>12} {'@ Conc':>8} {'Lat(avg)':>10}")
    print("-" * 70)

    for (service, scenario), runs in sorted(grouped.items()):
        peak = max(runs, key=lambda x: x.rps)
        lat = f"{peak.latency_avg_ms:.2f}ms" if peak.latency_avg_ms else "N/A"
        print(f"{service:<10} {scenario:<25} {peak.rps:>12,.0f} {peak.concurrency:>8} {lat:>10}")


def check_services():
    """Check which services are running."""
    print("\nChecking services...")
    available = []

    for key, svc in SERVICES.items():
        try:
            result = subprocess.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{svc['port']}/health",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip() == "200":
                print(f"  {svc['name']:>10}: OK (port {svc['port']})")
                available.append(key)
            else:
                print(f"  {svc['name']:>10}: DOWN")
        except:
            print(f"  {svc['name']:>10}: DOWN")

    return available


def run_full_benchmark():
    """
    Run the complete benchmark with correct isolation:
    1. Test each backend service individually (with restart + full inventory)
    2. Test Nginx with all services fresh
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_v2_{timestamp}.csv"

    all_results = []

    # Phase 1: Test each backend service individually
    print("\n" + "=" * 70)
    print("PHASE 1: Individual Service Benchmarks")
    print("=" * 70)

    for service_key in ["csharp", "java", "python"]:
        for scenario_key in ["small_biz", "big_biz"]:
            print(f"\n>>> Testing {SERVICES[service_key]['name']} with {SCENARIOS[scenario_key]['name']}")

            # Step 1: Reset Redis inventory to FULL
            print(f"    Resetting inventory to {SCENARIOS[scenario_key]['total_inventory']:,} items...")
            reset_redis_inventory(scenario_key)

            # Step 2: Restart the service to reload fresh allocations
            if not restart_service(service_key):
                print(f"    SKIPPING: Service {service_key} failed to restart")
                continue

            # Step 3: Run adaptive benchmark
            results = run_adaptive_benchmark_isolated(service_key, scenario_key)
            all_results.extend(results)

    # Phase 2: Test Nginx load balancer
    print("\n" + "=" * 70)
    print("PHASE 2: Nginx Load Balancer Benchmark")
    print("=" * 70)

    for scenario_key in ["small_biz", "big_biz"]:
        print(f"\n>>> Testing Nginx LB with {SCENARIOS[scenario_key]['name']}")

        # Step 1: Reset Redis inventory for ALL campaigns
        print(f"    Resetting all inventory pools...")
        for sc_key in SCENARIOS:
            reset_redis_inventory(sc_key)

        # Step 2: Restart ALL backend services
        if not restart_all_services():
            print(f"    SKIPPING: Some services failed to restart")
            continue

        # Step 3: Run adaptive benchmark through Nginx
        results = run_adaptive_benchmark_isolated("nginx", scenario_key)
        all_results.extend(results)

    # Save results
    write_csv(all_results, csv_file)
    analyze_results(all_results)

    return csv_file


def run_service_only(service_key: str):
    """Run benchmark for a single service only (both scenarios)."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_v2_{service_key}_{timestamp}.csv"

    all_results = []

    for scenario_key in ["small_biz", "big_biz"]:
        print(f"\n>>> Testing {SERVICES[service_key]['name']} with {SCENARIOS[scenario_key]['name']}")

        # Reset inventory
        print(f"    Resetting inventory to {SCENARIOS[scenario_key]['total_inventory']:,} items...")
        reset_redis_inventory(scenario_key)

        # Restart service (skip for nginx - handled separately)
        if service_key != "nginx":
            if not restart_service(service_key):
                print(f"    SKIPPING: Service {service_key} failed to restart")
                continue
        else:
            # For nginx, restart all backend services
            for sc_key in SCENARIOS:
                reset_redis_inventory(sc_key)
            if not restart_all_services():
                print(f"    SKIPPING: Backend services failed to restart")
                continue

        # Run benchmark
        results = run_adaptive_benchmark_isolated(service_key, scenario_key)
        all_results.extend(results)

    write_csv(all_results, csv_file)
    analyze_results(all_results)

    return csv_file


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python adaptive_benchmark_v2.py <command>")
        print("\nCommands:")
        print("  check     - Check which services are running")
        print("  full      - Run FULL benchmark (all services × all scenarios)")
        print("  csharp    - Benchmark C# only (small_biz + big_biz)")
        print("  java      - Benchmark Java only (small_biz + big_biz)")
        print("  python    - Benchmark Python only (small_biz + big_biz)")
        print("  nginx     - Benchmark Nginx LB only (small_biz + big_biz)")
        print("\nNotes:")
        print("  - Each service is tested in ISOLATION")
        print("  - Service is RESTARTED before each scenario")
        print("  - Inventory is RESET before each concurrency level")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        check_services()

    elif command == "full":
        run_full_benchmark()

    elif command in ["csharp", "java", "python", "nginx"]:
        run_service_only(command)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
