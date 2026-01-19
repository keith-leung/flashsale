import asyncio
import time
import httpx
from statistics import mean

async def run_benchmark(concurrency, duration_seconds):
    url = 'http://localhost:8000/api/v1/orders/'
    data = {
        'customer_name': 'Benchmark User',
        'customer_email': 'bench@example.com',
        'line_items': [{
            'sku_id': '2c2e23fa-f47b-4884-9b45-bf2a640f1ff3',
            'quantity': 1
        }]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = time.time()
        end_time = start_time + duration_seconds
        success_count = 0
        error_count = 0
        latencies = []
        
        async def worker():
            nonlocal success_count, error_count
            while time.time() < end_time:
                req_start = time.time()
                try:
                    response = await client.post(url, json=data)
                    req_end = time.time()
                    latencies.append((req_end - req_start) * 1000)
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
        
        tasks = [worker() for _ in range(concurrency)]
        await asyncio.gather(*tasks)
        
        actual_duration = time.time() - start_time
        throughput = success_count / actual_duration
        avg_latency = mean(latencies) if latencies else 0
        
        return {
            'concurrency': concurrency,
            'duration': actual_duration,
            'success': success_count,
            'errors': error_count,
            'throughput': throughput,
            'avg_latency_ms': avg_latency,
            'error_rate': (error_count / (success_count + error_count) * 100) if (success_count + error_count) > 0 else 0
        }

async def main():
    print('\n' + '='*70)
    print('VARIANT Z BENCHMARK - Token Pre-Allocation System')
    print('='*70)
    print(f'SKU: 2c2e23fa-f47b-4884-9b45-bf2a640f1ff3')
    print(f'Campaign: e26bb7d0-c863-4cd6-b08c-44fcca0a8c28')
    print('='*70 + '\n')
    
    results = []
    for concurrency in [10, 20, 50, 100]:
        result = await run_benchmark(concurrency, 10)
        results.append(result)
        print(f'Concurrency: {result["concurrency"]:3d} | Throughput: {result["throughput"]:6.2f} req/s | Avg Latency: {result["avg_latency_ms"]:6.2f}ms | Errors: {result["errors"]:4d} ({result["error_rate"]:4.1f}%)')
        await asyncio.sleep(2)
    
    print('\n' + '='*70)
    print('BENCHMARK SUMMARY')
    print('='*70)
    total_success = sum(r['success'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    avg_throughput = mean(r['throughput'] for r in results)
    avg_latency = mean(r['avg_latency_ms'] for r in results)
    overall_error_rate = (total_errors / (total_success + total_errors) * 100) if (total_success + total_errors) > 0 else 0
    
    print(f'Total Orders Created: {total_success}')
    print(f'Total Errors: {total_errors}')
    print(f'Average Throughput: {avg_throughput:.2f} req/s')
    print(f'Average Latency: {avg_latency:.2f}ms')
    print(f'Overall Error Rate: {overall_error_rate:.1f}%')
    print('='*70)

if __name__ == "__main__":
    asyncio.run(main())