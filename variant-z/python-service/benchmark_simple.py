#!/usr/bin/env python3
"""
Simple Python benchmark script for Variant Z Python service.
Tests order creation performance with concurrent requests.
"""

import asyncio
import argparse
import time
import json
from datetime import datetime
from typing import Dict, List
import httpx


class BenchmarkResults:
    """Track benchmark results."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.errors: Dict[str, int] = {}
        self.latencies: List[float] = []
        self.start_time = None
        self.end_time = None
    
    def add_success(self, latency: float):
        self.successful_requests += 1
        self.total_requests += 1
        self.latencies.append(latency)
    
    def add_failure(self, error: str = "unknown"):
        self.failed_requests += 1
        self.total_requests += 1
        self.errors[error] = self.errors.get(error, 0) + 1
    
    def get_stats(self) -> Dict:
        if not self.latencies:
            return {
                "total_requests": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "duration_sec": 0,
                "req_per_sec": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
            }
        
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        sorted_latencies = sorted(self.latencies)
        
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "duration_sec": round(duration, 2),
            "req_per_sec": round(self.total_requests / duration, 2) if duration > 0 else 0,
            "avg_latency_ms": round(sum(self.latencies) / len(self.latencies) * 1000, 2),
            "p50_latency_ms": round(sorted_latencies[len(sorted_latencies) // 2] * 1000, 2),
            "p95_latency_ms": round(sorted_latencies[int(len(sorted_latencies) * 0.95)] * 1000, 2),
            "p99_latency_ms": round(sorted_latencies[int(len(sorted_latencies) * 0.99)] * 1000, 2),
        }


async def create_order(client: httpx.AsyncClient, url: str, sku_id: str, results: BenchmarkResults):
    """Create a single order."""
    order_data = {
        "customer_name": "Benchmark Customer",
        "customer_email": "benchmark@example.com",
        "line_items": [{"sku_id": sku_id, "quantity": 1}],
        "currency": "USD"
    }
    
    start = time.time()
    try:
        response = await client.post(url, json=order_data, timeout=30.0)
        latency = time.time() - start
        
        if response.status_code in [200, 201]:
            results.add_success(latency)
        else:
            error_detail = response.text[:100]
            results.add_failure(f"HTTP_{response.status_code}")
    except Exception as e:
        latency = time.time() - start
        results.add_failure(f"{type(e).__name__}")


async def benchmark_worker(worker_id: int, url: str, sku_id: str, 
                          requests_per_worker: int, results: BenchmarkResults):
    """Worker that sends requests."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(requests_per_worker):
            await create_order(client, url, sku_id, results)
            
            if (i + 1) % 100 == 0:
                print(f"  Worker {worker_id}: {i + 1}/{requests_per_worker} requests completed")


async def run_benchmark(base_url: str, sku_id: str, total_requests: int, 
                       concurrency: int = 50):
    """Run the benchmark."""
    print("=" * 70)
    print("Variant Z Python Service - Simple Benchmark")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print(f"Total Requests: {total_requests}")
    print(f"Concurrency: {concurrency}")
    print(f"SKU ID: {sku_id}")
    print("=" * 70)
    print()
    
    # Health check
    print("1. Health Check...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health", timeout=5.0)
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
    print(f"   Sending {total_requests} requests with {concurrency} concurrent workers")
    print()
    
    results = BenchmarkResults()
    requests_per_worker = total_requests // concurrency
    
    results.start_time = time.time()
    
    # Create workers
    tasks = [
        benchmark_worker(i, f"{base_url}/api/v1/orders", sku_id, 
                        requests_per_worker, results)
        for i in range(concurrency)
    ]
    
    await asyncio.gather(*tasks)
    
    results.end_time = time.time()
    
    # Print results
    print()
    print("=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    
    stats = results.get_stats()
    print(f"Total Requests:      {stats['total_requests']}")
    print(f"Successful:          {stats['successful']}")
    print(f"Failed:              {stats['failed']}")
    print(f"Duration:            {stats['duration_sec']}s")
    print(f"Requests/sec:        {stats['req_per_sec']}")
    print()
    print("Latency:")
    print(f"  Average:           {stats['avg_latency_ms']}ms")
    print(f"  P50 (median):      {stats['p50_latency_ms']}ms")
    print(f"  P95:               {stats['p95_latency_ms']}ms")
    print(f"  P99:               {stats['p99_latency_ms']}ms")
    
    if results.errors:
        print()
        print("Errors:")
        for error, count in sorted(results.errors.items(), key=lambda x: -x[1]):
            print(f"  {error}: {count}")
    
    print()
    print("=" * 70)
    print("Performance Analysis")
    print("=" * 70)
    
    target_rps = 3000
    actual_rps = stats['req_per_sec']
    
    if actual_rps >= target_rps:
        print(f"✓ Target achieved: {actual_rps:.2f} req/s (target: {target_rps} req/s)")
    else:
        print(f"✗ Target missed: {actual_rps:.2f} req/s (target: {target_rps} req/s)")
        print(f"  Performance: {actual_rps / target_rps * 100:.1f}% of target")
    
    print()
    print("To verify data integrity:")
    print(f"  docker exec flash-mariadb-z mysql -u syracuse -pOrange_315_Forever! orange315 -e 'SELECT COUNT(*) FROM orders;'")
    print()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_variant_z_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "base_url": base_url,
            "sku_id": sku_id,
            "total_requests": total_requests,
            "concurrency": concurrency,
            "stats": stats,
            "errors": results.errors,
        }, f, indent=2)
    
    print(f"Results saved to: {filename}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simple benchmark for Variant Z Python service"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:30017",
        help="Base URL of the service (default: http://localhost:30017)"
    )
    parser.add_argument(
        "--sku-id",
        required=True,
        help="SKU ID to use for orders (get from setup_test_data.py)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10000,
        help="Total number of requests to send (default: 10000)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Number of concurrent workers (default: 50)"
    )
    
    args = parser.parse_args()
    
    await run_benchmark(
        base_url=args.url,
        sku_id=args.sku_id,
        total_requests=args.requests,
        concurrency=args.concurrency
    )


if __name__ == "__main__":
    asyncio.run(main())