"""Test script for order creation - Variant Z."""

import asyncio
import httpx
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_order_creation(base_url: str = "http://localhost:30017", sku_id: str = None):
    """Test order creation endpoint."""
    
    if not sku_id:
        logger.error("SKU ID is required. Please provide a valid SKU ID.")
        return
    
    # Test data
    order_data = {
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "line_items": [
            {
                "sku_id": sku_id,
                "quantity": 1
            }
        ],
        "currency": "USD"
    }
    
    url = f"{base_url}/api/v1/orders"
    
    logger.info("=" * 70)
    logger.info("TESTING ORDER CREATION - VARIANT Z")
    logger.info("=" * 70)
    logger.info(f"URL: {url}")
    logger.info(f"SKU ID: {sku_id}")
    logger.info(f"Order Data: {json.dumps(order_data, indent=2)}")
    logger.info("=" * 70)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = datetime.now()
            
            response = await client.post(
                url,
                json=order_data,
                headers={"Content-Type": "application/json"}
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Duration: {duration:.3f}s")
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✓ Order created successfully!")
                logger.info(f"Order ID: {result.get('order_id')}")
                logger.info(f"Total Amount: ${result.get('total_amount')}")
                logger.info(f"Status: {result.get('status')}")
            else:
                logger.error(f"✗ Order creation failed!")
                logger.error(f"Response: {response.text}")
            
            logger.info("=" * 70)
            
            return response
            
    except httpx.ConnectError:
        logger.error("✗ Connection refused. Is the service running?")
        return None
    except Exception as e:
        logger.error(f"✗ Error: {e}")
        return None


async def test_health_check(base_url: str = "http://localhost:30017"):
    """Test health check endpoint."""
    url = f"{base_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200 and response.text == "200 OK":
                logger.info("✓ Health check passed")
                return True
            else:
                logger.error(f"✗ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"✗ Health check error: {e}")
        return False


async def main():
    """Main test function."""
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:30017"
    sku_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Test health check
    logger.info("Testing health check...")
    if not await test_health_check(base_url):
        logger.error("Service is not healthy. Exiting.")
        return
    
    # Test order creation
    if sku_id:
        await test_order_creation(base_url, sku_id)
    else:
        logger.error("Please provide SKU ID as second argument")
        logger.info("Usage: python test_order.py [base_url] [sku_id]")
        logger.info("Example: python test_order.py http://localhost:30017 <sku-id>")


if __name__ == "__main__":
    asyncio.run(main())