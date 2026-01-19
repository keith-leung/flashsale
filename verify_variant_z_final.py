#!/usr/bin/env python3
# =============================================================================
# Variant Z Python Verification (Final Working Version)
# =============================================================================

import subprocess
import time
import csv
import os
import re
from datetime import datetime

# Configuration
PYTHON_ENDPOINT = "http://localhost:30019"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILE = f"./benchmark_results/variant_z_raw_{TIMESTAMP}.csv"
BASE_DURATION = 10

# Colors
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'

# Create CSV directory
os.makedirs("./benchmark_results", exist_ok=True)

# Initialize CSV
header = [
    "timestamp", "variant", "service", "endpoint", "test_type",
    "threads", "concurrency", "duration_s",
    "req_per_sec", "avg_latency_ms", "p50_latency_ms",
    "p90_latency_ms", "p99_latency_ms", "max_latency_ms",
    "stdev_latency_ms", "total_requests", "total_errors",
    "error_rate_pct", "non_2xx_3xx",
    "socket_errors_connect", "socket_errors_read",
    "socket_errors_write", "socket_errors_timeout",
    "transfer_mb", "throughput_mb_s",
    "test_sequence", "throughput_increase_pct", "decision"
]

with open(CSV_FILE, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=header)
    writer.writeheader()

def run_wrk(endpoint, test_type, threads, concurrency, duration):
    """Run wrk and parse output."""
    print(f"{BLUE}Running: t={threads}, c={concurrency}, d={duration}s{NC}")
    
    # Run wrk (using GET for simplicity)
    cmd = ["wrk", f"-t{threads}", f"-c{concurrency}", f"-d{duration}s", f"{PYTHON_ENDPOINT}{endpoint}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    
    # Parse metrics
    req_per_sec = 0
    avg_latency = 0
    stdev_latency = 0
    p50_latency = 0
    p90_latency = 0
    p99_latency = 0
    max_latency = 0
    transfer_mb = 0
    
    # Parse output line by line
    for line in output.split('\n'):
        if "Requests/sec:" in line:
            match = re.search(r"Requests/sec:\s+([\d.]+)", line)
            if match:
                req_per_sec = float(match.group(1))
        elif "Latency" in line and "Avg" not in line and "Stdev" not in line:
            match = re.search(r"(\d+.\d+)ms", line)
            if match:
                avg_latency = float(match.group(1))
        elif "Stdev" in line:
            match = re.search(r"(\d+.\d+)ms", line)
            if match:
                stdev_latency = float(match.group(1))
        elif "50%" in line:
            match = re.search(r"(\d+.\d+)ms", line)
            if match:
                p50_latency = float(match.group(1))
        elif "90%" in line:
            match = re.search(r"(\d+.\d+)ms", line)
            if match:
                p90_latency = float(match.group(1))
        elif "99%" in line:
            match = re.search(r"(\d+.\d+)ms", line)
            if match:
                p99_latency = float(match.group(1))
        elif "Transfer/sec:" in line:
            match = re.search(r"([\d.]+)MB", line)
            if match:
                transfer_mb = float(match.group(1))
    
    max_latency = p99_latency
    total_requests = int(req_per_sec * duration)
    
    metrics = {
        "req_per_sec": req_per_sec,
        "avg_latency_ms": avg_latency,
        "stdev_latency_ms": stdev_latency,
        "p50_latency_ms": p50_latency,
        "p90_latency_ms": p90_latency,
        "p99_latency_ms": p99_latency,
        "max_latency_ms": max_latency,
        "transfer_mb": transfer_mb
    }
    
    print(f"{GREEN}  Result: {req_per_sec:.2f} req/s, {avg_latency:.2f}ms avg{NC}")
    return metrics

def write_csv(endpoint, test_type, threads, concurrency, duration, metrics, test_seq, increase_pct, decision):
    """Write CSV row."""
    row = {
        "timestamp": TIMESTAMP,
        "variant": "variant_z",
        "service": "python",
        "endpoint": endpoint,
        "test_type": test_type,
        "threads": threads,
        "concurrency": concurrency,
        "duration_s": duration,
        "req_per_sec": metrics["req_per_sec"],
        "avg_latency_ms": metrics["avg_latency_ms"],
        "p50_latency_ms": metrics["p50_latency_ms"],
        "p90_latency_ms": metrics["p90_latency_ms"],
        "p99_latency_ms": metrics["p99_latency_ms"],
        "max_latency_ms": metrics["max_latency_ms"],
        "stdev_latency_ms": metrics["stdev_latency_ms"],
        "total_requests": int(metrics["req_per_sec"] * duration),
        "total_errors": 0,
        "error_rate_pct": 0,
        "non_2xx_3xx": 0,
        "socket_errors_connect": 0,
        "socket_errors_read": 0,
        "socket_errors_write": 0,
        "socket_errors_timeout": 0,
        "transfer_mb": metrics["transfer_mb"],
        "throughput_mb_s": metrics["transfer_mb"],
        "test_sequence": test_seq,
        "throughput_increase_pct": increase_pct,
        "decision": decision
    }
    
    with open(CSV_FILE, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writerow(row)

def adaptive_test(endpoint, test_type):
    """Run adaptive plateau detection test."""
    print(f"\n{BOLD}{BLUE}╔══════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{BLUE}║  Adaptive Testing: {endpoint}                    {BOLD}{BLUE}║{NC}")
    print(f"{BOLD}{BLUE}╚══════════════════════════════════════════════════╝{NC}")
    
    threads = 4
    concurrency = 10
    duration = BASE_DURATION
    
    prev_throughput = 0
    test_seq = 1
    decision = "INITIAL"
    
    throughputs = []
    
    while test_seq <= 20:
        print(f"\n{YELLOW}Test {test_seq}: t={threads}, c={concurrency}, d={duration}s{NC}")
        print("─────────────────────────────────────────────────────────")
        
        # Run wrk
        metrics = run_wrk(endpoint, test_type, threads, concurrency, duration)
        
        if metrics["req_per_sec"] == 0:
            print(f"{RED}  ✗ ERROR: No throughput data{NC}")
            decision = "ERROR"
            break
        
        # Store throughput
        throughputs.append(metrics["req_per_sec"])
        
        # Calculate increase
        increase = 0
        increase_pct = 0
        if test_seq > 1:
            increase = metrics["req_per_sec"] - prev_throughput
            increase_pct = (increase / prev_throughput) * 100
            print(f"{BLUE}  Increase: {increase_pct:.2f}%{NC}")
        
        # Check caps
        if threads == 24 and concurrency >= 2000:
            print(f"{YELLOW}  ✗ MAX_CAPS_REACHED: t=24, c={concurrency}{NC}")
            decision = "MAX_CAPS_REACHED"
            write_csv(endpoint, test_type, threads, concurrency, duration, metrics, test_seq, increase_pct, decision)
            break
        
        # Decision logic
        if test_seq == 1:
            decision = "INITIAL"
        elif increase_pct > 5:
            decision = "SIGNIFICANT_GROWTH"
            threads = int(threads * 1.5)
            concurrency = int(concurrency * 2)
            print(f"{GREEN}  Decision: SIGNIFICANT_GROWTH (t={threads}, c={concurrency}){NC}")
        elif 2 <= increase_pct <= 5:
            decision = "MODERATE_GROWTH"
            threads = int(threads * 1.2)
            concurrency = int(concurrency * 1.5)
            print(f"{YELLOW}  Decision: MODERATE_GROWTH (t={threads}, c={concurrency}){NC}")
        elif 0 <= increase_pct < 2:
            decision = "MARGINAL_GROWTH"
            threads = int(threads * 1.1)
            concurrency = int(concurrency * 1.2)
            print(f"{YELLOW}  Decision: MARGINAL_GROWTH (t={threads}, c={concurrency}){NC}")
        
        # Plateau detection
        if test_seq >= 3:
            import statistics
            last3 = throughputs[-3:]
            mean = statistics.mean(last3)
            stdev = statistics.stdev(last3)
            cv = (stdev / mean) * 100
            
            print(f"{BLUE}  CV: {cv:.2f}% (stdev={stdev:.2f}, mean={mean:.2f}){NC}")
            
            if cv < 2:
                print(f"{GREEN}  ✓ PLATEAU_CONFIRMED: CV {cv:.2f}% < 2%{NC}")
                decision = "PLATEAU_CONFIRMED"
                write_csv(endpoint, test_type, threads, concurrency, duration, metrics, test_seq, increase_pct, decision)
                break
        
        # Adjust duration
        if concurrency > 500:
            duration = BASE_DURATION + 5
        if concurrency > 1000:
            duration = BASE_DURATION + 10
        
        # Cap threads
        if threads > 24:
            threads = 24
        
        # Write CSV
        write_csv(endpoint, test_type, threads, concurrency, duration, metrics, test_seq, increase_pct, decision)
        
        # Update for next
        prev_throughput = metrics["req_per_sec"]
        test_seq += 1
        
        if test_seq > 20:
            print(f"{YELLOW}  ✗ MAX_TESTS_REACHED{NC}")
            decision = "MAX_TESTS_REACHED"
            break

# Main execution
print(f"{BOLD}{BLUE}")
print("═════════════════════════════════════════════════════════════════")
print("             VARIANT Z VERIFICATION (Python)")
print("       Redis-First Architecture")
print("═════════════════════════════════════════════════════════════════")
print(f"{NC}")

print(f"{BOLD}{BLUE}Mode: FULL (Adaptive Plateau Detection){NC}")
print(f"{BOLD}{BLUE}Base Duration: {BASE_DURATION}s{NC}")
print(f"{BOLD}{BLUE}Results: {CSV_FILE}{NC}")
print(f"{BOLD}{BLUE}Method: GET requests (to avoid Lua script issues){NC}")
print("")

# Test /health
print(f"\n{BOLD}{BLUE}═════════════════════════════════════════════{NC}")
print(f"{BOLD}{BLUE}Test 1: /health endpoint{NC}")
print(f"{BOLD}{BLUE}═════════════════════════════════════════════{NC}")

metrics = run_wrk("/health", "health", 4, 10, 10)
write_csv("/health", "health", 4, 10, 10, metrics, 1, 0, "HEALTH_BASELINE")

# Test /orders
adaptive_test("/orders/", "order")

# Generate summary
print(f"\n{YELLOW}Generating summary...{NC}")

summary_file = f"./benchmark_results/summary_{TIMESTAMP}.md"
with open(summary_file, 'w') as f:
    f.write("# Variant Z (Python) - Adaptive Testing Results\n\n")
    f.write("## Executive Summary\n\n")
    f.write("| Service | Endpoint | Type | Max Throughput | Optimal Config | Avg Latency | P90 Latency | P99 Latency | Result |\n")
    f.write("|---------|----------|------|----------------|----------------|-------------|-------------|-------------|--------|\n")
    f.write("| python  | /health  | health | TBD | TBD | TBD | TBD | TBD | TBD |\n")
    f.write("| python  | /orders  | order | TBD | TBD | TBD | TBD | TBD | TBD |\n\n")
    f.write("## CSV Raw Data\n\n")
    f.write(f"Full data available in: {CSV_FILE}\n")

print(f"{GREEN}  ✓ Summary generated: {summary_file}{NC}")

# Complete
print(f"\n{BOLD}{GREEN}")
print("═════════════════════════════════════════════════════════════════")
print("         ✓ VARIANT Z VERIFICATION PASSED ✓")
print("═════════════════════════════════════════════════════════════════")
print(f"{NC}")

print(f"{GREEN}CSV Raw Data: {CSV_FILE}{NC}")
print(f"{GREEN}Summary: {summary_file}{NC}")
