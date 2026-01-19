#!/usr/bin/env python3
"""Test stock limit"""

import asyncio
import httpx

async def test_stock_limit():
    """Test ordering more than available stock"""
    
    print("=== Test: Stock Limit ===\n")
    print(f"Current Stock: 8896")
    print(f"Attempting to order: 8897 (should fail)\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/api/v1/orders/",
            json={
                "customer_name": "Test User",
                "customer_email": "test@example.com",
                "line_items": [{
                    "sku_id": "2c2e23fa-f47b-4884-9b45-bf2a640f1ff3",
                    "quantity": 8897  # Exceeds available stock
                }]
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

asyncio.run(test_stock_limit())
