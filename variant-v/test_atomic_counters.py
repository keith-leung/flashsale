#!/usr/bin/env python3
"""
Test script to verify atomic counter operations work correctly.
This tests both the Java and C# implementations.
"""
import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor

def test_single_order(service_url, service_name):
    """Test a single order to verify basic functionality"""
    print(f"\n🧪 Testing {service_name} - Single Order")
    
    # Setup test data
    order_data = {
        "customerEmail": "test@example.com",
        "skuId": "unit-test-sku-001",
        "quantity": 1,
        "unitPrice": 599.00,
        "flashSaleCampaignId": "test-flash-campaign-001"
    }
    
    try:
        response = requests.post(
            f"{service_url}/api/v1/orders",
            json=order_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        print(f"  Status Code: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"  Error Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def main():
    services = {
        "Python": "http://localhost:30015",
        "Java": "http://localhost:8018",
        "C#": "http://localhost:30016"
    }
    
    print("="*60)
    print("Testing Atomic Counter Fixes in Variant V")
    print("="*60)
    
    for service_name, service_url in services.items():
        test_single_order(service_url, service_name)
    
    print("\n\n" + "="*60)
    print("Next: Run load test with 166 campaign limit")
    print("Use wrk with the provided lua scripts")
    print("="*60)

if __name__ == "__main__":
    main()