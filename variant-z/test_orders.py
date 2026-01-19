import asyncio
import httpx
import time

SKU_ID = "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3"

async def create_order(client, order_num):
    """Create a single order."""
    try:
        response = await client.post(
            'http://localhost:8000/api/v1/orders/',
            json={
                'customer_name': f'Customer {order_num}',
                'customer_email': f'customer{order_num}@example.com',
                'line_items': [{'sku_id': SKU_ID, 'quantity': 1}]
            },
            timeout=10.0
        )
        return response.status_code == 201, response.status_code
    except Exception as e:
        return False, str(e)

async def main():
    print("=" * 60)
    print("VARIANT Z ORDER CREATION TEST")
    print("=" * 60)
    print(f"SKU ID: {SKU_ID}")
    print(f"Test time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    async with httpx.AsyncClient() as client:
        # Test 1: Single order
        print("Test 1: Creating single order...")
        success, status = await create_order(client, 1)
        print(f"  Status: {status}")
        print(f"  Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
        print()
        
        # Test 2: 10 concurrent orders
        print("Test 2: Creating 10 concurrent orders...")
        start = time.time()
        tasks = [create_order(client, i) for i in range(2, 12)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        success_count = sum(1 for s, _ in results if s)
        print(f"  Successful: {success_count}/10")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {10/duration:.2f} req/s")
        print()
        
        # Test 3: 50 concurrent orders
        print("Test 3: Creating 50 concurrent orders...")
        start = time.time()
        tasks = [create_order(client, i) for i in range(12, 62)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        success_count = sum(1 for s, _ in results if s)
        print(f"  Successful: {success_count}/50")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {50/duration:.2f} req/s")
        print()
        
        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())