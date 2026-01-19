#!/usr/bin/env python3
"""Test Order API for Variant Zeta"""

import asyncio
import httpx
import json

async def test_order_api():
    """Test order creation API"""
    
    # Test 1: Health check
    print("=== Test 1: Health Check ===")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            print(f"Health status: {response.status_code}")
            print(f"Health response: {response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test 2: Get test data endpoint
    print("\n=== Test 2: Test Data Endpoint ===")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/api/v1/orders/test-data")
            print(f"Test data status: {response.status_code}")
            print(f"Test data response: {response.text}")
    except Exception as e:
        print(f"Test data endpoint failed: {e}")
    
    # Test 3: Create order
    print("\n=== Test 3: Create Order ===")
    order_request = {
        "customer_name": "Test User",
        "customer_email": "test@example.com",
        "line_items": [{
            "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
            "quantity": 1
        }]
    }
    
    try:
        import time
        start = time.time()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/orders/",
                json=order_request
            )
            
            elapsed = time.time() - start
            print(f"Order status: {response.status_code}")
            print(f"Order time: {elapsed*1000:.2f}ms")
            print(f"Order response: {response.text}")
            
            if response.status_code == 201:
                print("✓ Order created successfully!")
            else:
                print(f"✗ Order failed with status {response.status_code}")
    except Exception as e:
        print(f"Create order failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_order_api())
