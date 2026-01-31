#!/usr/bin/env python3
"""
Variant A Adaptive Benchmark: Finding Peak/Plateau Performance
Similar to Sacred Variant Y verification - tests multiple concurrency levels
to find optimal throughput.
"""

import subprocess
import time
import csv
import os
import re
from datetime import datetime
from dataclasses import dataclass
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
        "prealloc_pct": 100,  # 100% pre-allocation
    },
    "big_biz": {
        "campaign_id": "00000002-0000-0000-0000-000000000001",
        "sku_id": "00000002-0000-0000-0000-000000000003",
        "name": "Big Business (1M items)",
        "total_inventory": 1000000,
        "prealloc_pct": 10,  # 10% pre-allocation, 90% Redis pool
    },
    "real_campaign": {
        "campaign_id": "99999999-8888-7777-6666-555544443333",
        "sku_id": "11111111-2222-3333-4444-555555555555",
        "name": "Real Campaign (existing)",
        "total_inventory": 100000000,
        "prealloc_pct": 5,
    }
}

SERVICES = {
    "csharp": {"port": 30014, "name": "C#", "threads": 8},
    "java": {"port": 8017, "name": "Java", "threads": 4},
    "python": {"port": 30013, "name": "Python", "threads": 4},
    "nginx": {"port": 8445, "name": "Nginx LB", "threads": 8},
}

# Adaptive benchmark concurrency levels
CONCURRENCY_LEVELS = [10, 25, 50, 100, 150, 200, 300, 400]

# Benchmark duration per test (seconds)
DURATION = 10


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


def setup_redis_pool(scenario_key: str) -> int:
    """Setup Redis inventory pools for a scenario."""
    scenario = SCENARIOS[scenario_key]
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total_inventory"]

    # Set large pool for testing
    pool_size = total

    cmds = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {pool_size}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {pool_size}',
    ]

    for cmd in cmds:
        subprocess.run(cmd, shell=True, capture_output=True)

    return pool_size


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
    path = "/tmp/wrk_adaptive.lua"
    with open(path, "w") as f:
        f.write(script)
    return path


def run_single_benchmark(service_key: str, scenario_key: str, concurrency: int) -> BenchmarkResult:
    """Run a single benchmark at specified concurrency."""
    service = SERVICES[service_key]
    scenario = SCENARIOS[scenario_key]

    script_path = create_wrk_script(scenario["sku_id"])
    protocol = "https" if service.get("https") else "http"
    url = f"{protocol}://localhost:{service['port']}/api/v1/orders"
    threads = min(service["threads"], concurrency)

    # Add -k flag for HTTPS to ignore certificate errors
    k_flag = "-k" if service.get("https") else ""
    cmd = f"wrk -t{threads} -c{concurrency} -d{DURATION}s {k_flag} -s {script_path} {url} 2>&1"

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


def run_adaptive_benchmark(service_key: str, scenario_key: str) -> List[BenchmarkResult]:
    """Run adaptive benchmark across all concurrency levels."""
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
        # Reset Redis pool before each test
        setup_redis_pool(scenario_key)
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
            writer.writerow(r.__dict__)

    print(f"\nResults saved to: {filename}")


def analyze_results(filename: str):
    """Analyze and summarize results from CSV."""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    print(f"\n{'='*70}")
    print("BENCHMARK ANALYSIS")
    print(f"{'='*70}\n")

    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        results = list(reader)

    # Group by service and scenario
    from collections import defaultdict
    grouped = defaultdict(list)

    for r in results:
        key = (r["service"], r["scenario"])
        grouped[key].append(r)

    # Find peak for each service/scenario
    print(f"{'Service':<10} {'Scenario':<25} {'Peak RPS':>12} {'@ Conc':>8} {'Lat(avg)':>10}")
    print("-" * 70)

    summary = []
    for (service, scenario), runs in sorted(grouped.items()):
        peak = max(runs, key=lambda x: float(x["rps"]))
        lat = f"{float(peak['latency_avg_ms']):.2f}ms" if peak['latency_avg_ms'] else "N/A"
        print(f"{service:<10} {scenario:<25} {float(peak['rps']):>12,.0f} {peak['concurrency']:>8} {lat:>10}")
        summary.append({
            "service": service,
            "scenario": scenario,
            "peak_rps": float(peak["rps"]),
            "optimal_concurrency": int(peak["concurrency"]),
            "latency_avg_ms": float(peak["latency_avg_ms"]) if peak["latency_avg_ms"] else 0
        })

    return summary


def check_services():
    """Check which services are running."""
    print("\nChecking services...")
    available = []

    for key, svc in SERVICES.items():
        try:
            protocol = "https" if svc.get("https") else "http"
            k_flag = "-k" if svc.get("https") else ""
            result = subprocess.run(
                f"curl -s {k_flag} -o /dev/null -w '%{{http_code}}' {protocol}://localhost:{svc['port']}/health",
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


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python adaptive_benchmark.py <command>")
        print("\nCommands:")
        print("  check      - Check which services are running")
        print("  run        - Run adaptive benchmark (real_campaign, all services)")
        print("  quick      - Quick benchmark (real_campaign only, all services)")
        print("  small_biz  - Small Business scenario (5K items, 100% pre-alloc)")
        print("  big_biz    - Big Business scenario (1M items, 10% pre-alloc)")
        print("  full       - Full benchmark (small_biz + big_biz, all services)")
        print("  analyze    - Analyze latest results")
        print("  csharp     - Benchmark C# only (real_campaign)")
        print("  java       - Benchmark Java only (real_campaign)")
        print("  python     - Benchmark Python only (real_campaign)")
        print("  nginx      - Benchmark Nginx LB only (real_campaign)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        check_services()

    elif command == "run":
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_adaptive_{timestamp}.csv"

        available = check_services()
        if not available:
            print("No services available!")
            sys.exit(1)

        all_results = []
        scenarios_to_test = ["real_campaign"]  # Start with existing campaign

        for scenario in scenarios_to_test:
            for service in available:
                results = run_adaptive_benchmark(service, scenario)
                all_results.extend(results)

        write_csv(all_results, csv_file)
        analyze_results(csv_file)

    elif command == "quick":
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_quick_{timestamp}.csv"

        available = check_services()
        if not available:
            print("No services available!")
            sys.exit(1)

        all_results = []
        for service in available:
            results = run_adaptive_benchmark(service, "real_campaign")
            all_results.extend(results)

        write_csv(all_results, csv_file)
        analyze_results(csv_file)

    elif command in ["csharp", "java", "python", "nginx"]:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_{command}_{timestamp}.csv"

        results = run_adaptive_benchmark(command, "real_campaign")
        write_csv(results, csv_file)
        analyze_results(csv_file)

    elif command == "small_biz":
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_small_biz_{timestamp}.csv"

        available = check_services()
        if not available:
            print("No services available!")
            sys.exit(1)

        all_results = []
        for service in available:
            # Reset Redis pool before each service test
            setup_redis_pool("small_biz")
            results = run_adaptive_benchmark(service, "small_biz")
            all_results.extend(results)

        write_csv(all_results, csv_file)
        analyze_results(csv_file)

    elif command == "big_biz":
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_big_biz_{timestamp}.csv"

        available = check_services()
        if not available:
            print("No services available!")
            sys.exit(1)

        all_results = []
        for service in available:
            # Reset Redis pool before each service test
            setup_redis_pool("big_biz")
            results = run_adaptive_benchmark(service, "big_biz")
            all_results.extend(results)

        write_csv(all_results, csv_file)
        analyze_results(csv_file)

    elif command == "full":
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_full_{timestamp}.csv"

        available = check_services()
        if not available:
            print("No services available!")
            sys.exit(1)

        all_results = []
        for scenario in ["small_biz", "big_biz"]:
            print(f"\n{'='*70}")
            print(f"SCENARIO: {SCENARIOS[scenario]['name']}")
            print(f"{'='*70}")
            for service in available:
                # Reset Redis pool before each service test
                setup_redis_pool(scenario)
                results = run_adaptive_benchmark(service, scenario)
                all_results.extend(results)

        write_csv(all_results, csv_file)
        analyze_results(csv_file)

    elif command == "analyze":
        import glob
        files = glob.glob("/home/syracuse/flashsale/benchmark_results/variant_a_*.csv")
        if files:
            latest = max(files, key=os.path.getctime)
            analyze_results(latest)
        else:
            print("No benchmark files found")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
