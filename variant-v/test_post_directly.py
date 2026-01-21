#!/usr/bin/env python3
"""Direct POST test for orders."""

import requests
import json

print("Testing POST directly...")

url = "http://localhost:30017/api/v1/orders"
headers = {"Content-Type": "application/json"}
data = {
    "customer_email": "test@example.com",
    "items": [
        {
            "sku_id": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
            "quantity": 2,
            "unit_price": 49.99
        }
    ],
    "flash_sale_campaign_id": "test-flash-campaign-001"
}

try:
    print(f"POST {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    resp = requests.post(url, json=data, headers=headers, timeout=10)
    
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {resp.text}")
    print(f"Headers: {dict(resp.headers)}")
    
    if resp.status_code == 201:
        result = resp.json()
        print(f"\n✓ Order created! Audit ID: {result.get('audit_id')}")
    elif resp.status_code == 409:
        print("\n✓ Order rejected (campaign limits)")
    elif resp.status_code == 405:
        print("\n✗ Method not allowed - router issue")
    else:
        print(f"\n? Unexpected status: {resp.status_code}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
