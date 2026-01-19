#!/usr/bin/env python3
"""Test full design implementation"""

import asyncio
import httpx
import time

async def test_order_api():
    """Test order API"""
    
    print("=== Testing Full Design Implementation ===\n")
    
    # Test 1: Health check
    print("Test 1: Health Check (API)")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:30019/health")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 2: Create order
    print("\nTest 2: Create Order")
    order_request = {
        "customer_name": "Full Design Test User",
        "customer_email": "fulldesign@example.com",
        "line_items": [{
            "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
            "quantity": 1
        }]
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start = time.time()
            response = await client.post(
                "http://localhost:30019/api/v1/orders/",
                json=order_request
            )
            elapsed = (time.time() - start) * 1000
            
            print(f"  Status: {response.status_code}")
            print(f"  Latency: {elapsed:.2f}ms")
            print(f"  Response: {response.text[:200]}")
            
            if response.status_code == 201:
                order_id = response.json()['order_id']
                print(f"  ✓ Order created: {order_id}")
                
                # Test 3: Check if order is queued
                print(f"\nTest 3: Check Order Status")
                await asyncio.sleep(2)
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('localhost', 6379))
                s.sendall(f"GET order:{order_id}:status\r\n".encode())
                response = s.recv(1024).decode()
                print(f"  Redis order status: {response}")
                s.close()
    except Exception as e:
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_order_api())
