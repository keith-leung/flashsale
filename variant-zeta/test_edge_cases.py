#!/usr/bin/env python3
"""Test edge cases for Order API"""

import asyncio
import httpx
import json

async def test_edge_cases():
    """Test edge cases"""
    
    print("=== Edge Cases Test ===\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # Test 1: Non-existent SKU (should fail)
        print("Test 1: Non-existent SKU")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/orders/",
                json={
                    "customer_name": "Test User",
                    "customer_email": "test@example.com",
                    "line_items": [{
                        "sku_id": "non-existent-sku-id",
                        "quantity": 1
                    }]
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 2: Invalid quantity (should fail validation)
        print("\nTest 2: Invalid quantity (0)")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/orders/",
                json={
                    "customer_name": "Test User",
                    "customer_email": "test@example.com",
                    "line_items": [{
                        "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
                        "quantity": 0
                    }]
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 3: Negative quantity (should fail validation)
        print("\nTest 3: Negative quantity")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/orders/",
                json={
                    "customer_name": "Test User",
                    "customer_email": "test@example.com",
                    "line_items": [{
                        "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
                        "quantity": -1
                    }]
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 4: Valid order (should succeed)
        print("\nTest 4: Valid order")
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/orders/",
                json={
                    "customer_name": "Test User",
                    "customer_email": "test@example.com",
                    "line_items": [{
                        "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
                        "quantity": 1
                    }]
                }
            )
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")

asyncio.run(test_edge_cases())
