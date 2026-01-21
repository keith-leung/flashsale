#!/usr/bin/env python3
"""Test Java and C# API endpoints after fixing the contracts."""

import requests
import json
import sys

def test_java_service():
    """Test Java service API."""
    print("Testing Java service...")
    url = "http://localhost:8018/api/v1/orders"
    headers = {"Content-Type": "application/json"}
    data = {
        "customerEmail": "test@example.com",
        "skuId": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
        "quantity": 1,
        "unitPrice": 599.00,
        "flashSaleCampaignId": "test-flash-campaign-001"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Java Status: {response.status_code}")
        print(f"Java Response: {response.text[:200]}")
        return response.status_code
    except Exception as e:
        print(f"Java Error: {e}")
        return None

def test_csharp_service():
    """Test C# service API."""
    print("\nTesting C# service...")
    url = "http://localhost:30016/api/v1/orders"
    headers = {"Content-Type": "application/json"}
    data = {
        "CustomerEmail": "test@example.com",
        "SkuId": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
        "Quantity": 1,
        "UnitPrice": 599.00,
        "FlashSaleCampaignId": "test-flash-campaign-001"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"C# Status: {response.status_code}")
        print(f"C# Response: {response.text[:200]}")
        return response.status_code
    except Exception as e:
        print(f"C# Error: {e}")
        return None

if __name__ == "__main__":
    java_status = test_java_service()
    csharp_status = test_csharp_service()
    
    if java_status == 201 or java_status == 409:
        print("\n✓ Java service API working")
    else:
        print(f"\n✗ Java service failed with status: {java_status}")
        
    if csharp_status == 201 or csharp_status == 409:
        print("✓ C# service API working")
    else:
        print(f"✗ C# service failed with status: {csharp_status}")
        
    if (java_status in [201, 409]) and (csharp_status in [201, 409]):
        print("\n✓ Both services API contracts fixed and working!")
        sys.exit(0)
    else:
        print("\n✗ Services still have issues")
        sys.exit(1)
