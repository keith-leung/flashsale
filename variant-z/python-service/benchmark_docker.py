#!/usr/bin/env python3
"""Simple benchmark script that runs inside the Docker container."""

import asyncio
import time
import json
from datetime import datetime

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.run(["pip", "install", "httpx"], check=True)
    import httpx


async def benchmark():
    """Run benchmark against the Python service."""
    
    # Configuration
    BASE_URL = "http://localhost:8000"  # Inside container
    SKU_ID = "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3"
    TOTAL_REQUESTS = 5000
    CONCURRENCY = 50
    
    print("=" * 70)
    print("Variant Z Python Service - Simple Benchmark")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Total Requests: {TOTAL_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"SKU ID: {SKU_ID}")
    print("=" * 70)
    print()
    
    # Health check
    print("1. Health Check...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200 and response.text == "200 OK":
                print("   ✓ Health check passed")
            else:
                print(f"   ✗ Health check failed: {response.status_code}")
                return
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        return
    
    print()
    print("2. Starting Benchmark...")
    print(f"   Sending {TOTAL_REQUESTS} requests with {CONCURRENCY} concurrent workers")
    print()
    
    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "latencies": []
    }
    
    async def create_order(client):
        """Create a single order."""
        order_data = {
            "customer_name": "Benchmark Customer",
            "customer_email": "benchmark@example.com",
            "line_items": [{"sku_id": SKU_ID, "quantity": 1}],
            "currency": "USD"
        }
        
        start = time.time()
        try:
            response = await client.post(f"{BASE_URL}/api/v1/orders/", json=order_data, timeout=30.0)
            latency = time.time() - start
            
            results["total"] += 1
            if response.status_code in [200, 201]:
                results["success"] += 1
                results["latencies"].append(latency)
            else:
                results["failed"] += 1
        except Exception as e:
            results["total"] += 1
            results["failed"] += 1
    
    start_time = time.time()
    
    # Create concurrent workers
    async with httpx.AsyncClient(timeout=60.0, limits=httpx.Limits(max_connections=100)) as client:
        tasks = []
        requests_per_worker = TOTAL_REQUESTS // CONCURRENCY
        
        for i in range(CONCURRENCY):
            for j in range(requests_per_worker):
                tasks.append(create_order(client))
        
        # Execute all requests
        await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate statistics
    if results["latencies"]:
        avg_latency = sum(results["latencies"]) / len(results["latencies"]) * 1000
        sorted_latencies = sorted(results["latencies"])
        p50 = sorted_latencies[len(sorted_latencies) // 2] * 1000
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] * 1000
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] * 1000
    else:
        avg_latency = p50 = p95 = p99 = 0
    
    rps = results["total"] / duration if duration > 0 else 0
    
    # Print results
    print()
    print("=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(f"Total Requests:      {results['total']}")
    print(f"Successful:          {results['success']}")
    print(f"Failed:              {results['failed']}")
    print(f"Duration:            {duration:.2f}s")
    print(f"Requests/sec:        {rps:.2f}")
    print()
    print("Latency:")
    print(f"  Average:           {avg_latency:.2f}ms")
    print(f"  P50 (median):      {p50:.2f}ms")
    print(f"  P95:               {p95:.2f}ms")
    print(f"  P99:               {p99:.2f}ms")
    print("=" * 70)
    print()
    
    # Performance analysis
    target_rps = 3000
    if rps >= target_rps:
        print(f"✓ Target achieved: {rps:.2f} req/s (target: {target_rps} req/s)")
    else:
        print(f"✗ Target missed: {rps:.2f} req/s (target: {target_rps} req/s)")
        print(f"  Performance: {rps / target_rps * 100:.1f}% of target")
    
    print()
    print("To verify data integrity:")
    print("  docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'")
    print()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_variant_z_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "base_url": BASE_URL,
            "sku_id": SKU_ID,
            "total_requests": TOTAL_REQUESTS,
            "concurrency": CONCURRENCY,
            "results": results,
            "duration_sec": round(duration, 2),
            "req_per_sec": round(rps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
        }, f, indent=2)
    
    print(f"Results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(benchmark())