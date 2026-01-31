#!/usr/bin/env python3
"""
Variant A Benchmark: Small Biz vs Big Biz Scenarios
Based on Gemini's design guide for database-driven flash sale testing.
"""

import subprocess
import json
import time
import csv
import os
from datetime import datetime, timedelta

# ============================================================================
# MATH SECTION: Calculating Safe Parameters
# ============================================================================
"""
Little's Law for Refill Mechanism:
- L = λ * W (items in system = arrival rate * wait time)

For Scenario B (Big Business):
- Target RPS per instance: 50,000
- Refill network latency: ~20ms = 0.020 seconds
- Items consumed during one refill: 50,000 * 0.020 = 1,000 items

Safety margin (2x): RefillChunkSize = 2,000 items minimum
Recommended: RefillChunkSize = 5,000 items (5x safety margin)

LowWatermark Calculation:
- Should trigger refill BEFORE stock hits zero
- At 50k RPS, 5,000 items last: 5,000 / 50,000 = 100ms
- Trigger at 30% remaining = 1,500 items = 30ms buffer
- This gives us 30ms to complete the 20ms refill

For Scenario A (Small Business):
- Total items: 5,000
- 3 instances: ~1,667 items each
- Pre-allocate 100% to avoid refills entirely
- Set watermark to 0 (no refills needed)
"""

# Configuration
SCENARIOS = {
    "small_biz": {
        "campaign_id": "00000001-0000-0000-0000-000000000001",
        "spu_id": "00000001-0000-0000-0000-000000000002",
        "sku_id": "00000001-0000-0000-0000-000000000003",
        "name": "Small Business Flash Sale",
        "total_inventory": 5000,
        "flash_price": 9.99,
        "ordinary_price": 19.99,
        # 100% pre-allocation across 3 instances
        "preallocate_percentage": 100,
        "csharp_ratio": 34,  # Gets ~34% = 1700 items
        "java_ratio": 33,    # Gets ~33% = 1650 items
        "python_ratio": 33,  # Gets ~33% = 1650 items
        "refill_watermark_pct": 0,  # No refills - sell from RAM only
        "description": "5K items, 100% pre-alloc, no refills"
    },
    "big_biz": {
        "campaign_id": "00000002-0000-0000-0000-000000000001",
        "spu_id": "00000002-0000-0000-0000-000000000002",
        "sku_id": "00000002-0000-0000-0000-000000000003",
        "name": "Big Business Flash Sale",
        "total_inventory": 1000000,
        "flash_price": 49.99,
        "ordinary_price": 99.99,
        # 10% initial pre-allocation, rest in Redis pool for refills
        "preallocate_percentage": 10,
        "csharp_ratio": 34,
        "java_ratio": 33,
        "python_ratio": 33,
        "refill_watermark_pct": 30,  # Trigger refill at 30% remaining
        "description": "1M items, 10% pre-alloc, sustained refills"
    }
}

# Service endpoints
SERVICES = {
    "csharp": {"port": 30014, "name": "C# ASP.NET"},
    "java": {"port": 8017, "name": "Java Spring"},
    "python": {"port": 30013, "name": "Python FastAPI"},
    "nginx": {"port": 8446, "name": "Nginx Load Balancer", "https": True}
}

def create_sql_setup():
    """Generate SQL to create the test campaigns."""

    sql = """
-- ============================================================================
-- Variant A Benchmark: Campaign Setup SQL
-- ============================================================================

-- Clean up existing test campaigns
DELETE FROM flash_sale_campaigns WHERE id IN (
    '00000001-0000-0000-0000-000000000001',
    '00000002-0000-0000-0000-000000000001'
);
DELETE FROM skus WHERE id IN (
    '00000001-0000-0000-0000-000000000003',
    '00000002-0000-0000-0000-000000000003'
);
DELETE FROM spus WHERE id IN (
    '00000001-0000-0000-0000-000000000002',
    '00000002-0000-0000-0000-000000000002'
);

-- Create SPUs for test campaigns
INSERT INTO spus (id, name, description, is_active, created_at, updated_at) VALUES
('00000001-0000-0000-0000-000000000002', 'Small Biz Product', 'Test product for small business scenario', 1, NOW(), NOW()),
('00000002-0000-0000-0000-000000000002', 'Big Biz Product', 'Test product for big business scenario', 1, NOW(), NOW());

-- Create SKUs with inventory
INSERT INTO skus (id, spu_id, sku_code, name, price, is_active, track_inventory, created_at, updated_at) VALUES
('00000001-0000-0000-0000-000000000003', '00000001-0000-0000-0000-000000000002', 'SMALL-001', 'Small Biz SKU', 19.99, 1, 1, NOW(), NOW()),
('00000002-0000-0000-0000-000000000003', '00000002-0000-0000-0000-000000000002', 'BIG-001', 'Big Biz SKU', 99.99, 1, 1, NOW(), NOW());

-- Create inventory records
INSERT INTO inventories (id, sku_id, quantity, reserved_quantity, allow_negative_stock, created_at, updated_at) VALUES
(UUID(), '00000001-0000-0000-0000-000000000003', 5000, 0, 0, NOW(), NOW()),
(UUID(), '00000002-0000-0000-0000-000000000003', 1000000, 0, 0, NOW(), NOW());

-- ============================================================================
-- SCENARIO A: Small Business (5,000 items, 100% pre-allocation)
-- ============================================================================
INSERT INTO flash_sale_campaigns (
    id, spu_id, name, flash_price,
    total_sale_limit, preallocate_percentage,
    csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
    refill_lower_watermark_pct,
    start_time, end_time, status, is_active, created_at, updated_at
) VALUES (
    '00000001-0000-0000-0000-000000000001',
    '00000001-0000-0000-0000-000000000002',
    'Small Business Flash Sale',
    9.99,
    5000,      -- Total inventory
    100,       -- 100% pre-allocation (no refills needed)
    34, 33, 33, -- Ratio: C# 34%, Java 33%, Python 33%
    0,         -- 0% watermark = no refill trigger
    NOW(),
    DATE_ADD(NOW(), INTERVAL 30 DAY),
    'active',
    1,
    NOW(), NOW()
);

-- ============================================================================
-- SCENARIO B: Big Business (1,000,000 items, sustained refills)
-- ============================================================================
INSERT INTO flash_sale_campaigns (
    id, spu_id, name, flash_price,
    total_sale_limit, preallocate_percentage,
    csharp_allocation_ratio, java_allocation_ratio, python_allocation_ratio,
    refill_lower_watermark_pct,
    start_time, end_time, status, is_active, created_at, updated_at
) VALUES (
    '00000002-0000-0000-0000-000000000001',
    '00000002-0000-0000-0000-000000000002',
    'Big Business Flash Sale',
    49.99,
    1000000,   -- 1 Million items
    10,        -- 10% initial pre-allocation (100k items)
    34, 33, 33,
    30,        -- 30% watermark = trigger refill early
    NOW(),
    DATE_ADD(NOW(), INTERVAL 30 DAY),
    'active',
    1,
    NOW(), NOW()
);

-- Verify setup
SELECT
    id, name, total_sale_limit, preallocate_percentage,
    refill_lower_watermark_pct, status
FROM flash_sale_campaigns
WHERE id IN (
    '00000001-0000-0000-0000-000000000001',
    '00000002-0000-0000-0000-000000000001'
);
"""
    return sql


def setup_redis_pools(scenario_key):
    """Setup Redis inventory pools for a scenario."""
    scenario = SCENARIOS[scenario_key]
    campaign_id = scenario["campaign_id"]
    sku_id = scenario["sku_id"]
    total = scenario["total_inventory"]
    prealloc_pct = scenario["preallocate_percentage"]

    # Calculate Redis pool size (what's NOT pre-allocated to services)
    redis_pool = int(total * (100 - prealloc_pct) / 100)

    commands = [
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:spu_counter" {redis_pool}',
        f'podman exec flash-redis-a redis-cli SET "fs:{campaign_id}:redis_pool:sku:{sku_id}" {redis_pool}',
    ]

    print(f"\n=== Setting up Redis pools for {scenario['name']} ===")
    print(f"Total inventory: {total}")
    print(f"Pre-allocated to services: {total - redis_pool} ({prealloc_pct}%)")
    print(f"Redis pool for refills: {redis_pool} ({100 - prealloc_pct}%)")

    for cmd in commands:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
        else:
            print(f"OK: {result.stdout.strip()}")

    return redis_pool


def create_wrk_script(scenario_key):
    """Create wrk Lua script for a scenario."""
    scenario = SCENARIOS[scenario_key]
    sku_id = scenario["sku_id"]

    script = f'''
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

local counter = 0

request = function()
    counter = counter + 1
    local body = string.format([[{{
        "customer_email": "bench%d@test.com",
        "customer_name": "Benchmark User %d",
        "line_items": [{{"sku_id": "{sku_id}", "quantity": 1}}],
        "tax_amount": 0,
        "shipping_amount": 0,
        "currency": "USD"
    }}]], counter, counter)
    return wrk.format(nil, nil, nil, body)
end
'''

    script_path = f"/tmp/wrk_{scenario_key}.lua"
    with open(script_path, "w") as f:
        f.write(script)

    return script_path


def run_benchmark(service_key, scenario_key, duration=10, connections=100, threads=4):
    """Run a single benchmark and return results."""
    service = SERVICES[service_key]
    scenario = SCENARIOS[scenario_key]
    script_path = create_wrk_script(scenario_key)

    protocol = "https" if service.get("https") else "http"
    url = f"{protocol}://localhost:{service['port']}/api/v1/orders"

    # Add -k for HTTPS to ignore certificate errors
    k_flag = "-k" if service.get("https") else ""

    cmd = f"wrk -t{threads} -c{connections} -d{duration}s {k_flag} -s {script_path} {url} 2>&1"

    print(f"\nRunning: {service['name']} / {scenario['name']}")
    print(f"Command: {cmd}")

    start_time = datetime.now()
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    end_time = datetime.now()

    output = result.stdout + result.stderr

    # Parse results
    rps = 0
    latency_avg = "N/A"
    latency_max = "N/A"
    errors = 0
    total_requests = 0

    for line in output.split('\n'):
        if 'Requests/sec:' in line:
            try:
                rps = float(line.split(':')[1].strip())
            except:
                pass
        if 'Latency' in line and 'Stdev' not in line:
            parts = line.split()
            if len(parts) >= 2:
                latency_avg = parts[1]
                if len(parts) >= 4:
                    latency_max = parts[3]
        if 'Non-2xx' in line:
            try:
                errors = int(line.split(':')[1].strip())
            except:
                pass
        if 'requests in' in line:
            try:
                total_requests = int(line.split()[0])
            except:
                pass

    return {
        "timestamp": start_time.isoformat(),
        "scenario": scenario_key,
        "scenario_name": scenario["name"],
        "service": service_key,
        "service_name": service["name"],
        "duration_sec": duration,
        "connections": connections,
        "threads": threads,
        "total_requests": total_requests,
        "requests_per_sec": rps,
        "latency_avg": latency_avg,
        "latency_max": latency_max,
        "non_2xx_errors": errors,
        "raw_output": output
    }


def write_csv_log(results, filename):
    """Write results to CSV activity log."""
    fieldnames = [
        "timestamp", "scenario", "scenario_name", "service", "service_name",
        "duration_sec", "connections", "threads", "total_requests",
        "requests_per_sec", "latency_avg", "latency_max", "non_2xx_errors"
    ]

    file_exists = os.path.exists(filename)

    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for result in results:
            # Don't write raw_output to CSV
            row = {k: v for k, v in result.items() if k in fieldnames}
            writer.writerow(row)

    print(f"\nResults appended to: {filename}")


def analyze_csv(filename):
    """Analyze results from CSV activity log."""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return

    print(f"\n{'='*70}")
    print(f"ANALYSIS: {filename}")
    print(f"{'='*70}")

    with open(filename, "r") as f:
        reader = csv.DictReader(f)
        results = list(reader)

    # Group by scenario and service
    from collections import defaultdict
    grouped = defaultdict(list)

    for r in results:
        key = (r["scenario"], r["service"])
        grouped[key].append(r)

    print(f"\n{'Scenario':<15} {'Service':<10} {'RPS':>12} {'Latency':>10} {'Errors':>8}")
    print("-" * 60)

    for (scenario, service), runs in sorted(grouped.items()):
        # Get latest run
        latest = runs[-1]
        rps = float(latest["requests_per_sec"]) if latest["requests_per_sec"] else 0
        print(f"{scenario:<15} {service:<10} {rps:>12,.0f} {latest['latency_avg']:>10} {latest['non_2xx_errors']:>8}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python benchmark_scenarios.py <command>")
        print("Commands:")
        print("  sql       - Generate SQL setup script")
        print("  redis     - Setup Redis pools for both scenarios")
        print("  run       - Run full benchmark suite")
        print("  analyze   - Analyze CSV results")
        sys.exit(1)

    command = sys.argv[1]

    if command == "sql":
        print(create_sql_setup())

    elif command == "redis":
        setup_redis_pools("small_biz")
        setup_redis_pools("big_biz")

    elif command == "run":
        results = []
        csv_file = f"/home/syracuse/flashsale/benchmark_results/variant_a_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)

        for scenario_key in ["small_biz", "big_biz"]:
            print(f"\n{'='*70}")
            print(f"SCENARIO: {SCENARIOS[scenario_key]['name']}")
            print(f"{'='*70}")

            # Setup Redis pools
            setup_redis_pools(scenario_key)

            # Wait for services to reload
            time.sleep(2)

            # Run benchmarks for each service
            for service_key in ["csharp", "java", "python"]:
                # Reset Redis pools between services
                setup_redis_pools(scenario_key)
                time.sleep(1)

                result = run_benchmark(
                    service_key=service_key,
                    scenario_key=scenario_key,
                    duration=10,
                    connections=100,
                    threads=4
                )
                results.append(result)
                print(f"  RPS: {result['requests_per_sec']:,.0f}, Errors: {result['non_2xx_errors']}")

        # Write results
        write_csv_log(results, csv_file)

        # Analyze
        analyze_csv(csv_file)

    elif command == "analyze":
        # Find latest CSV file
        import glob
        files = glob.glob("/home/syracuse/flashsale/benchmark_results/variant_a_benchmark_*.csv")
        if files:
            latest = max(files)
            analyze_csv(latest)
        else:
            print("No benchmark CSV files found")

    else:
        print(f"Unknown command: {command}")
