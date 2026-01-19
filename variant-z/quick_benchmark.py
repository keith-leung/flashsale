import asyncio
import time
import httpx

async def main():
    url = 'http://localhost:8000/api/v1/orders/'
    data = {'customer_name':'Test','customer_email':'test@example.com','line_items':[{'sku_id':'2c2e23fa-f47b-4884-9b45-bf2a640f1ff3','quantity':1}]}
    
    print("Testing order creation...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.time()
        tasks = [client.post(url, json=data) for _ in range(50)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start
        
        success = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        errors = len(responses) - success
        
        print(f"\n{'='*50}")
        print(f"VARIANT Z BENCHMARK RESULTS")
        print(f"{'='*50}")
        print(f"Concurrent Requests: 50")
        print(f"Successful Orders: {success}")
        print(f"Errors: {errors}")
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {success/duration:.2f} req/s")
        print(f"Error Rate: {errors/len(responses)*100:.1f}%")
        print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())