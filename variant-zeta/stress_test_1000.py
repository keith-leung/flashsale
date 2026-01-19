#!/usr/bin/env python3
"""Stress test Order API - 1000 orders"""

import asyncio
import httpx
import time
from statistics import mean, median, stdev

async def create_order(client, order_num):
    """Create single order"""
    order_request = {
        "customer_name": f"User {order_num}",
        "customer_email": f"user{order_num}@example.com",
        "line_items": [{
            "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
            "quantity": 1
        }]
    }
    
    try:
        start = time.time()
        response = await client.post(
            "http://localhost:8000/api/v1/orders/",
            json=order_request,
            timeout=30.0
        )
        elapsed = (time.time() - start) * 1000
        
        success = response.status_code == 201
        return {
            "success": success,
            "status_code": response.status_code,
            "time_ms": elapsed,
            "order_id": response.json().get("order_id") if success else None
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "time_ms": 0,
            "order_id": None,
            "error": str(e)
        }

async def main():
    """Run stress test"""
    print("=== Stress Test: 1000 Orders ===")
    print()
    
    # Configure client with connection pooling
    limits = httpx.Limits(max_keepalive_connections=200, max_connections=500)
    async with httpx.AsyncClient(limits=limits, timeout=60.0) as client:
        # Run 1000 orders concurrently
        start_time = time.time()
        tasks = [create_order(client, i) for i in range(1, 1001)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        success_rate = (len(successful) / len(results)) * 100
        
        times = [r["time_ms"] for r in results if r["time_ms"] > 0]
        
        print(f"Total Time: {total_time:.2f}s")
        print(f"Orders/sec: {len(results) / total_time:.2f}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Successful: {len(successful)}/1000")
        print(f"Failed: {len(failed)}/1000")
        
        if times:
            print(f"\nLatency (ms):")
            print(f"  Avg: {mean(times):.2f}")
            print(f"  Median: {median(times):.2f}")
            print(f"  Min: {min(times):.2f}")
            print(f"  Max: {max(times):.2f}")
            print(f"  P95: {sorted(times)[int(len(times)*0.95)]:.2f}")
            print(f"  P99: {sorted(times)[int(len(times)*0.99)]:.2f}")
            print(f"  StdDev: {stdev(times):.2f}")
        
        if failed:
            print(f"\nFailed Orders (first 10):")
            for f in failed[:10]:
                print(f"  Status {f.get('status_code')}: {f.get('error', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
