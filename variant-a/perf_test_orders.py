#!/usr/bin/env python3
"""
Performance Test for Python Order Processing - Variant A
Tests pure in-memory vs Redis-refill performance
"""
import asyncio
import aiohttp
import time
from typing import List, Tuple
import statistics

# Configuration
URL = "http://localhost:30013/api/v1/orders"
CAMPAIGN_ID = "perftest-camp-0000-0000-000000000001"
SKU_ID = "perftest-sku1-0000-0000-000000000001"

# Phase 1: Pure in-memory (no Redis hits)
PHASE1_ORDERS = 150000
PHASE1_CONCURRENCY = 200

# Phase 2: With Redis refills
PHASE2_ORDERS = 30000
PHASE2_CONCURRENCY = 200

async def create_order(session: aiohttp.ClientSession, order_num: int) -> Tuple[float, int, bool]:
    """Create a single order and measure latency."""
    payload = {
        "customer_email": f"perftest{order_num}@example.com",
        "customer_name": f"Perf Test {order_num}",
        "line_items": [{
            "sku_id": SKU_ID,
            "quantity": 1
        }],
        "flash_sale_campaign_id": CAMPAIGN_ID,
        "currency": "USD"
    }

    start = time.time()
    try:
        async with session.post(URL, json=payload) as resp:
            latency = time.time() - start
            data = await resp.json()
            success = resp.status == 201 or (resp.status == 200 and data.get("status") == 201)
            return (latency, resp.status, success)
    except Exception as e:
        latency = time.time() - start
        return (latency, 0, False)


async def run_phase(phase_name: str, num_orders: int, concurrency: int, start_order: int = 0):
    """Run a test phase with specified concurrency."""
    print(f"\n{'='*70}")
    print(f"  {phase_name}")
    print(f"{'='*70}")
    print(f"Orders: {num_orders:,}")
    print(f"Concurrency: {concurrency}")
    print("")

    latencies = []
    successes = 0
    failures = 0

    connector = aiohttp.TCPConnector(limit=concurrency)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Run in batches
        batch_size = concurrency * 10
        total_batches = (num_orders + batch_size - 1) // batch_size

        phase_start = time.time()
        order_count = 0

        for batch_num in range(total_batches):
            batch_start_order = start_order + (batch_num * batch_size)
            batch_orders = min(batch_size, num_orders - (batch_num * batch_size))

            # Create tasks for this batch
            tasks = [
                create_order(session, batch_start_order + i)
                for i in range(batch_orders)
            ]

            # Execute batch
            batch_start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_duration = time.time() - batch_start_time

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    failures += 1
                else:
                    latency, status, success = result
                    latencies.append(latency)
                    if success:
                        successes += 1
                    else:
                        failures += 1

            order_count += batch_orders
            elapsed = time.time() - phase_start
            throughput = order_count / elapsed if elapsed > 0 else 0

            # Progress update every 10 batches
            if (batch_num + 1) % 10 == 0 or batch_num == total_batches - 1:
                print(f"Progress: {order_count:,}/{num_orders:,} orders | " +
                      f"Throughput: {throughput:.1f} req/s | " +
                      f"Success: {successes:,} | Failed: {failures}")

    phase_duration = time.time() - phase_start

    # Calculate statistics
    if latencies:
        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        avg_latency = statistics.mean(latencies)
    else:
        p50 = p95 = p99 = avg_latency = 0

    throughput = successes / phase_duration if phase_duration > 0 else 0

    # Print results
    print(f"\n{phase_name} Results:")
    print(f"{'─'*70}")
    print(f"  Duration: {phase_duration:.2f}s")
    print(f"  Total Orders: {order_count:,}")
    print(f"  Successful: {successes:,}")
    print(f"  Failed: {failures}")
    print(f"  Throughput: {throughput:.2f} req/s")
    print(f"  Latency (avg): {avg_latency*1000:.2f}ms")
    print(f"  Latency (p50): {p50*1000:.2f}ms")
    print(f"  Latency (p95): {p95*1000:.2f}ms")
    print(f"  Latency (p99): {p99*1000:.2f}ms")

    return {
        "phase": phase_name,
        "duration": phase_duration,
        "orders": order_count,
        "successes": successes,
        "failures": failures,
        "throughput": throughput,
        "latency_avg": avg_latency * 1000,
        "latency_p50": p50 * 1000,
        "latency_p95": p95 * 1000,
        "latency_p99": p99 * 1000,
    }


async def main():
    print("\n" + "="*70)
    print("  Python Order Performance Test - Variant A")
    print("  Testing Adaptive Inventory Performance")
    print("="*70)

    # Check service health
    print("\n[Pre-check] Checking Python service...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:30013/health") as resp:
                if resp.status == 200:
                    print("✓ Python service ready")
                else:
                    print(f"✗ Python service returned status {resp.status}")
                    return
    except Exception as e:
        print(f"✗ Cannot connect to Python service: {e}")
        return

    # Phase 1: Pure in-memory
    print("\n" + "="*70)
    print("PHASE 1: PURE IN-MEMORY (Best Case - No Redis Hits)")
    print("="*70)
    print(f"Expected: All {PHASE1_ORDERS:,} orders served from local cache (176,470 items)")
    print("This measures PEAK performance with 99%+ zero network I/O")

    phase1_results = await run_phase(
        "Phase 1: Pure In-Memory",
        PHASE1_ORDERS,
        PHASE1_CONCURRENCY,
        start_order=1
    )

    # Phase 2: With Redis refills
    print("\n" + "="*70)
    print("PHASE 2: WITH REDIS REFILLS (Degraded Performance)")
    print("="*70)
    print(f"Expected: Redis refills triggered as cache depletes")
    print("This measures performance WITH network I/O overhead")

    phase2_results = await run_phase(
        "Phase 2: With Redis Refills",
        PHASE2_ORDERS,
        PHASE2_CONCURRENCY,
        start_order=PHASE1_ORDERS + 1
    )

    # Final summary
    print("\n" + "="*70)
    print("                  PERFORMANCE TEST SUMMARY")
    print("="*70)

    print(f"\n{'Phase':<30} {'Throughput':<20} {'Latency (avg)':<15} {'Latency (p99)':<15}")
    print("─"*80)
    print(f"{'Phase 1: Pure In-Memory':<30} "
          f"{phase1_results['throughput']:<20.2f} "
          f"{phase1_results['latency_avg']:<15.2f} "
          f"{phase1_results['latency_p99']:<15.2f}")
    print(f"{'Phase 2: With Redis Refills':<30} "
          f"{phase2_results['throughput']:<20.2f} "
          f"{phase2_results['latency_avg']:<15.2f} "
          f"{phase2_results['latency_p99']:<15.2f}")

    # Calculate degradation
    if phase1_results['throughput'] > 0:
        degradation = ((phase1_results['throughput'] - phase2_results['throughput']) /
                      phase1_results['throughput'] * 100)
        print(f"\n{'Performance Impact:':<30} "
              f"{degradation:.1f}% throughput reduction with Redis refills")

    print("\n" + "="*70)
    print("✓ Performance test completed!")
    print("="*70)

    # Check for Redis refills in logs
    print("\nTo check Redis refill events:")
    print("  docker exec flash-python-a grep '[SPU REFILL]' /var/log/flashsale/variant-a/orders_$(date +%Y%m%d).log")


if __name__ == "__main__":
    asyncio.run(main())
