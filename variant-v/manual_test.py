#!/usr/bin/env python3
"""Manual test using requests from host."""

import requests
import json

BASE_URL = "http://localhost:30017"
API_URL = f"{BASE_URL}/api/v1"

print("Testing health...")
resp = requests.get(f"{BASE_URL}/health")
print(f"Health: {resp.status_code} - {resp.text}")

print("\nTesting order...")
order_data = {
    "customer_email": "test@example.com",
    "items": [
        {
            "sku_id": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
            "quantity": 3,
            "unit_price": 49.99
        }
    ],
    "flash_sale_campaign_id": "test-flash-campaign-001"
}

try:
    resp = requests.post(f"{API_URL}/orders", json=order_data, timeout=10)
    print(f"Order status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
