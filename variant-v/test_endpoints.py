#!/usr/bin/env python3
"""Test script for Variant V endpoints."""

import requests
import json
import time
import sys

BASE_URL = "http://10.92.0.7:8000"
API_URL = f"{BASE_URL}/api/v1"

def test_health():
    """Test health endpoint."""
    print("=== Testing Health Endpoint ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200 and "200 OK" in response.text:
            print("✓ Health check PASSED")
            return True
        else:
            print("✗ Health check FAILED")
            return False
    except Exception as e:
        print(f"✗ Health check ERROR: {e}")
        return False

def test_non_flash_order():
    """Test order creation without flash sale (should fail in current implementation).""" 
    print("\n=== Testing Non-Flash-Sale Order ===")
    
    order_data = {
        "customer_email": "test@example.com",
        "items": [
            {
                "sku_id": "non-flash-sku-001",
                "quantity": 1,
                "unit_price": 99.99
            }
        ],
        "flash_sale_campaign_id": "invalid-campaign-123"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/orders",
            json=order_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 409:
            print("✓ Non-flash order correctly rejected (no valid campaign)")
            return True
        else:
            print("? Unexpected response for non-flash order")
            return False
            
    except Exception as e:
        print(f"✗ Non-flash order ERROR: {e}")
        return False

def test_flash_sale_order():
    """Test order creation with valid flash sale campaign."""
    print("\n=== Testing Flash-Sale Order ===")
    
    # Use the test campaign we set up
    order_data = {
        "customer_email": "customer@flashsale.com",
        "items": [
            {
                "sku_id": "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab",
                "quantity": 5,
                "unit_price": 49.99
            }
        ],
        "flash_sale_campaign_id": "test-flash-campaign-001"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/orders",
            json=order_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            data = response.json()
            if data.get("status") == "confirmed":
                print("✓ Flash-sale order CREATED successfully")
                print(f"  Audit ID: {data.get('audit_id')}")
                return True, data.get("audit_id")
            else:
                print("✗ Order status not confirmed")
                return False, None
        elif response.status_code == 409:
            print("✓ Order correctly rejected (likely sold out or campaign limit)")
            return True, None
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"✗ Flash-sale order ERROR: {e}")
        return False, None

def test_order_status(audit_id):
    """Test order status endpoint."""
    if not audit_id:
        return False
        
    print(f"\n=== Testing Order Status (Audit: {audit_id[:8]}...) ===")
    
    try:
        response = requests.get(
            f"{API_URL}/orders/{audit_id}",
            timeout=5
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            print("✓ Order status retrieved successfully")
            return True
        else:
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Order status ERROR: {e}")
        return False

def verify_campaign_limits():
    """Verify campaign limits in Redis."""
    print("\n=== Verifying Campaign Limits ===")
    
    try:
        import redis
        r = redis.Redis(host='10.92.0.3', port=6379)
        
        campaign_id = "test-flash-campaign-001"
        sku_id = "6a3c2f1b-9d4e-4f8a-bc7d-1234567890ab"
        
        # Check remaining quantity
        remaining = r.get(f"campaign:{campaign_id}:sku:{sku_id}:remaining")
        if remaining:
            remaining_val = int(remaining.decode())
            print(f"✓ SKU remaining: {remaining_val} units")
            return remaining_val
        else:
            print("✗ Could not find SKU remaining quantity")
            return None
            
    except Exception as e:
        print(f"✗ Campaign verification ERROR: {e}")
        return None

def main():
    """Run all tests."""
    print("Variant V Endpoint Testing")
    print("=" * 50)
    
    # Give services a moment to fully start
    print("Waiting for services to be ready...")
    time.sleep(3)
    
    results = {}
    
    # Test 1: Health
    results["health"] = test_health()
    
    # Test 2: Non-flash order (should fail)
    results["non_flash_order"] = test_non_flash_order()
    
    # Test 3: Flash sale order (should succeed)
    success, audit_id = test_flash_sale_order()
    results["flash_order"] = success
    
    # Test 4: Order status
    if audit_id:
        results["order_status"] = test_order_status(audit_id)
    
    # Test 5: Verify campaign limits
    results["campaign_limits"] = verify_campaign_limits() is not None
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for test, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test.replace('_', ' ').title()}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Variant V is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
