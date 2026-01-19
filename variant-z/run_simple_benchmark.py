"""Simple Python benchmark for Variant Z order creation."""

import asyncio
import httpx
import time
from datetime import datetime

# Test SKU with available tokens
SKU_ID = "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3"

async def create_order(client, order_num):
    """Create a single order."""
    try:
        response = await client.post(
            'http://flash-python-z:8000/api/v1/orders/',
            json={
                'customer_name': f'Customer {order_num}',
                'customer_email': f'customer{order_num}@example.com',
                'line_items': [{'sku_id': SKU_ID, 'quantity': 1}]
            },
            timeout=5.0
        )
        return response.status_code == 201
    except Exception as e:
        print(f"Error creating order {order_num}: {e}")
        return False

async def benchmark(concurrency, duration_seconds):
    """Run benchmark with given concurrency and duration."""
    print(f"\n{'='*60}")
    print(f"Benchmark: concurrency={concurrency}, duration={duration_seconds}s")
    print(f"{'='*60}")
    
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=100)) as client:
        order_num = 0
        success_count = 0
        error_count = 0
        
        while time.time() < end_time:
            # Create batch of concurrent requests
            tasks = []
            for _ in range(concurrency):
                order_num += 1
                tasks.append(create_order(client, order_num))
            
            # Execute batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes
            for result in results:
                if result is True:
                    success_count += 1
                elif result is False:
                    error_count += 1
                else:
                    error_count += 1  # Exception
        
        total_duration = time.time() - start_time
        throughput = success_count / total_duration
        
        print(f"\nResults:")
        print(f"  Total Orders:    {order_num}")
        print(f"  Successful:       {success_count}")
        print(f"  Errors:          {error_count}")
        print(f"  Duration:         {total_duration:.2f}s")
        print(f"  Throughput:       {throughput:.2f} req/s")
        
        return throughput, success_count, error_count

async def main():
    """Run adaptive benchmark."""
    print("\n" + "="*60)
    print("VARIANT Z ORDER BENCHMARK - SIMPLE PYTHON VERSION")
    print("="*60)
    print(f"SKU ID: {SKU_ID}")
    print(f"Test time: {datetime.utcnow().isoformat()}")
    
    # Test 1: Low concurrency
    await benchmark(concurrency=10, duration_seconds=10)
    await asyncio.sleep(2)
    
    # Test 2: Moderate concurrency
    await benchmark(concurrency=20, duration_seconds=10)
    await asyncio.sleep(2)
    
    # Test 3: High concurrency
    await benchmark(concurrency=40, duration_seconds=10)
    
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())