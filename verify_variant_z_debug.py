#!/usr/bin/env python3
import subprocess
import re
import csv
import os
from datetime import datetime

PYTHON_ENDPOINT = "http://localhost:30019"
BEST_SKU = "e9d1b0af-f22b-11f0-bbc4-9660160e28bc"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = f"./benchmark_results/variant_z_raw_{TIMESTAMP}.csv"

os.makedirs("./benchmark_results", exist_ok=True)

# CSV header
header = ["timestamp", "variant", "service", "endpoint", "test_type",
    "threads", "concurrency", "duration_s",
    "req_per_sec", "avg_latency_ms", "p50_latency_ms",
    "p90_latency_ms", "p99_latency_ms", "max_latency_ms",
    "stdev_latency_ms", "total_requests", "total_errors",
    "error_rate_pct", "non_2xx_3xx",
    "socket_errors_connect", "socket_errors_read",
    "socket_errors_write", "socket_errors_timeout",
    "transfer_mb", "throughput_mb_s",
    "test_sequence", "throughput_increase_pct", "decision"]

with open(CSV_FILE, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=header)
    writer.writeheader()

def run_wrk_test(endpoint, test_type, threads, concurrency, duration, lua_script=None):
    print(f"\nRunning: t={threads}, c={concurrency}, d={duration}s")
    
    cmd = ["wrk", f"-t{threads}", f"-c{concurrency}", f"-d{duration}s"]
    if lua_script:
        cmd.extend(["-s", lua_script])
    cmd.append(f"{PYTHON_ENDPOINT}{endpoint}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    full_output = result.stdout + result.stderr
    
    print("Raw wrk output (first 20 lines):")
    for i, line in enumerate(full_output.split('\n')[:20], 1):
        print(f"  {i}: {line}")
    
    # Parse throughput
    req_per_sec_match = re.search(r"Requests/sec:\s+([\d.]+)", full_output)
    print(f"\nRegex match for Requests/sec: {req_per_sec_match}")
    
    if req_per_sec_match:
        req_per_sec = float(req_per_sec_match.group(1))
        print(f"Parsed req_per_sec: {req_per_sec}")
    else:
        req_per_sec = 0
        print(f"✗ Failed to parse Requests/sec")
    
    return req_per_sec

# Test /health
print("=" * 60)
print("Test 1: /health endpoint")
print("=" * 60)

metrics = run_wrk_test("/health", "health", 4, 10, 10)

# Test /orders
print("\n" + "=" * 60)
print("Test 2: /orders endpoint")
print("=" * 60)

metrics = run_wrk_test("/orders/", "order", 4, 10, 10, "/tmp/wrk_order_zeta.lua")

print(f"\n✓ Testing complete")
print(f"CSV: {CSV_FILE}")
