#!/usr/bin/env python3
"""
Adaptive performance benchmark for Variant V order endpoint.

This script tests the order API with increasing load to find the maximum 
sustainable throughput with realistic order patterns.
"""

import requests
import json
import time
import asyncio
import aiohttp
from typing import List, Dict, Any
import statistics

# Configuration
API_URL = "http://localhost:30017/api/v1/orders"
CAMPAIGN_ID = "test-flash-campaign-001"
TEST_SKU = "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab"
UNIT_PRICE = 49.99

async def place_order(session: aiohttp.ClientSession, order_data: Dict[str, Any]) -> tuple:
    """Place a single order and return the result."""
    start_time = time.time()
    try:
        async with session.post(API_URL, json=order_data) as response:
            result = {
                'status': response.status,
                'duration': time.time() - start_time,
                'error': None
            }
            if response.status >= 500:
                result['error'] = await response.text()
            return result
    except Exception as e:
        return {
            'status': 0,
            'duration': time.time() - start_time,
            'error': str(e)
        }

async def run_load_test(concurrent_requests: int, total_requests: int) -> List[Dict]:
    """Run a load test with specified concurrency."""
    # Prepare order data
    order_data = {
        "customer_email": f"test@concurrent.com",
        "items": [{"sku_id": TEST_SKU, "quantity": 1, "unit_price": UNIT_PRICE}],
        "flash_sale_campaign_id": CAMPAIGN_ID
    }
    
    results = []
    async with aiohttp.ClientSession() as session:
        # Create tasks
        tasks = []
        for _ in range(total_requests):
            task = place_order(session, order_data)
            tasks.append(task)
            
            # Control concurrency by submitting in batches
            if len(tasks) >= concurrent_requests:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                tasks = []
                await asyncio.sleep(0.001)  # Small delay between batches
        
        # Handle remaining tasks
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
    
    return results

def analyze_results(results: List[Dict]) -> Dict[str, float]:
    """Analyze test results and calculate metrics."""
    successful = [r for r in results if r['status'] in [200, 201]]
    rejected = [r for r in results if r['status'] == 409]
    failed = [r for r in results if r['status'] >= 500 or r['error']]
    
    durations = [r['duration'] for r in results]
    
    return {
        'total': len(results),
        'successful': len(successful),
        'rejected': len(rejected),
        'failed': len(failed),
        'success_rate': (len(successful) / len(results) * 100) if results else 0,
        'avg_duration': statistics.mean(durations) if durations else 0,
        'p95_duration': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else 0,
        'p99_duration': statistics.quantiles(durations, n=100)[98] if len(durations) > 100 else 0,
        'min_duration': min(durations) if durations else 0,
        'max_duration': max(durations) if durations else 0
    }

def print_report(metrics: Dict[str, float], concurrent_requests: int, elapsed: float):
    """Print a formatted report of test results."""
    throughput = metrics['total'] / elapsed
    
    print(f"\n{'='*70}")
    print(f"Load Test Results - {concurrent_requests} concurrent requests")
    print(f"{'='*70}")
    print(f"Duration:        {elapsed:.2f}s")
    print(f"Throughput:      {throughput:.2f} req/s")
    print(f"Success Rate:    {metrics['success_rate']:.1f}%")
    print(f"\nBreakdown:")
    print(f"  ✓ Successful:   {metrics['successful']}/{metrics['total']}")
    print(f"  ⊘ Rejected:     {metrics['rejected']}/{metrics['total']}")
    print(f"  ✗ Failed:       {metrics['failed']}/{metrics['total']}")
    print(f"\nResponse Times:")
    print(f"  Min:            {metrics['min_duration']*1000:.1f}ms")
    print(f"  Avg:            {metrics['avg_duration']*1000:.1f}ms")
    print(f"  P95:            {metrics['p95_duration']*1000:.1f}ms")
    print(f"  P99:            {metrics['p99_duration']*1000:.1f}ms")
    print(f"  Max:            {metrics['max_duration']*1000:.1f}ms")
    print(f"{'='*70}\n")
    
    return throughput

async def adaptive_benchmark():
    """Run adaptive benchmark starting from low load and scaling up."""
    print("Variant V Order Endpoint - Adaptive Performance Benchmark")
    print("=" * 70)
    
    # Test configurations (concurrent_requests, total_requests)
    test_configs = [
        (10, 100),      # Low load
        (50, 500),      # Medium load
        (100, 1000),    # High load
        (200, 2000),    # Stress test
    ]
    
    results = []
    
    for concurrent, total in test_configs:
        print(f"\nRunning test with {concurrent} concurrent requests ({total} total)...")
        
        start_time = time.time()
        test_results = await run_load_test(concurrent, total)
        elapsed = time.time() - start_time
        
        metrics = analyze_results(test_results)
        throughput = print_report(metrics, concurrent, elapsed)
        
        results.append({
            'concurrent': concurrent,
            'throughput': throughput,
            'metrics': metrics
        })
        
        # Adapt: If success rate drops below 95%, stop testing
        if metrics['success_rate'] < 95:
            print(f"⚠️  Success rate dropped below 95% ({metrics['success_rate']:.1f}%), stopping here.")
            break
        
        # Add delay between tests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("Adaptive Benchmark Summary")
    print("=" * 70)
    for i, result in enumerate(results):
        print(f"{i+1}. {result['concurrent']:>3} concurrent → {result['throughput']:>7.1f} req/s")
    
    return results

async def main():
    """Main benchmark execution."""
    try:
        results = await adaptive_benchmark()
        
        # Find maximum stable throughput
        max_throughput = max(r['throughput'] for r in results) if results else 0
        print(f"\n✓ Maximum sustained throughput: {max_throughput:.1f} req/s")
        
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
    except Exception as e:
        print(f"\n\nBenchmark failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
