"""
Test script for Order CRUD and workflow operations.
"""

import asyncio
import httpx
import json
import uuid

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"


class OrderCrudTester:
    """Order workflow tester"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
        self.test_run_id = uuid.uuid4().hex[:8]
        self.spu_id = None
        self.sku_id = None
        self.order_id = None
        self.spu_slug = f"test-spu-for-order-{self.test_run_id}"
        self.sku_code = f"TEST-ORDER-SKU-{self.test_run_id}"

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def print_section(self, title: str):
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_response(self, response: httpx.Response):
        print(f"Status: {response.status_code}")
        if response.status_code >= 400:
            print(f"Error: {response.text}")
        else:
            try:
                print(json.dumps(response.json(), indent=2, default=str))
            except json.JSONDecodeError:
                print(response.text)

    async def setup_dependencies(self):
        """Create prerequisite SPU, SKU, and Inventory."""
        self.print_section("SETUP: Create SPU, SKU, and Inventory")
        # Create SPU
        spu_data = {"name": f"Test SPU for Order {self.test_run_id}", "slug": self.spu_slug}
        spu_res = await self.client.post(f"{self.base_url}/spus", json=spu_data)
        if spu_res.status_code != 201:
            raise Exception(f"Setup failed: Could not create SPU. {spu_res.text}")
        self.spu_id = spu_res.json()["data"]["id"]
        print(f"✓ Prerequisite SPU created. ID: {self.spu_id}")

        # Create SKU with initial inventory
        sku_data = {
            "sku_code": self.sku_code,
            "name": f"Test SKU for Order {self.test_run_id}",
            "spu_id": self.spu_id,
            "price": 250.00,
            "initial_quantity": 100
        }
        sku_res = await self.client.post(f"{self.base_url}/skus", json=sku_data)
        if sku_res.status_code != 201:
            raise Exception(f"Setup failed: Could not create SKU. {sku_res.text}")
        self.sku_id = sku_res.json()["data"]["id"]
        print(f"✓ Prerequisite SKU created with initial inventory. ID: {self.sku_id}")

    async def create_order(self):
        """Create a new order."""
        self.print_section("CREATE ORDER")
        order_data = {
            "customer_email": f"customer-{self.test_run_id}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": self.sku_id, "quantity": 5}]
        }
        print(f"POST {self.base_url}/orders")
        print(f"Request: {json.dumps(order_data, indent=2, default=str)}")
        response = await self.client.post(f"{self.base_url}/orders", json=order_data)
        self.print_response(response)
        if response.status_code == 201:
            result = response.json()
            self.order_id = result["data"]["id"]
            print(f"\n✓ Order Created Successfully! ID: {self.order_id}")
            if result["data"]["status"] != "pending":
                raise Exception("Order status should be 'pending' on creation.")
            print("✓ Order status is 'pending' as expected.")
        else:
            raise Exception(f"Failed to create order: {response.text}")

    async def read_order(self):
        """Read the created order."""
        self.print_section("READ ORDER")
        print(f"GET {self.base_url}/orders/{self.order_id}")
        response = await self.client.get(f"{self.base_url}/orders/{self.order_id}")
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to read order: {response.text}")
        print("\n✓ Order Read Successfully!")

    async def create_payment(self):
        """Create a payment to confirm the order."""
        self.print_section("CREATE PAYMENT (Confirm Order)")
        payment_data = {"amount": 1250.00, "currency": "USD", "payment_method": "test_card"}
        response = await self.client.post(f"{self.base_url}/orders/{self.order_id}/payments", json=payment_data)
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to create payment: {response.text}")
        
        # Verify order status is now 'confirmed'
        order_res = await self.client.get(f"{self.base_url}/orders/{self.order_id}")
        if order_res.json()["data"]["status"] != "confirmed":
            raise Exception("Order status did not update to 'confirmed' after payment.")
        print("\n✓ Payment created and order status is 'confirmed'.")

    async def fulfill_order(self):
        """Fulfill the order."""
        self.print_section("FULFILL ORDER")
        response = await self.client.post(f"{self.base_url}/orders/{self.order_id}/fulfill")
        self.print_response(response)
        if response.status_code != 200 or response.json()["data"]["status"] != "shipped":
            raise Exception(f"Failed to fulfill order: {response.text}")
        print("\n✓ Order fulfilled and status is 'shipped'.")

    async def verify_inventory(self):
        """Verify inventory was deducted correctly."""
        self.print_section("VERIFY INVENTORY")
        response = await self.client.get(f"{self.base_url}/inventory/{self.sku_id}")
        self.print_response(response)
        inventory = response.json()["data"]
        if inventory["quantity"] != 95 or inventory["reserved_quantity"] != 0:
            raise Exception(f"Inventory not deducted correctly. Expected 95, got {inventory['quantity']}.")
        print("\n✓ Inventory correctly deducted (95) and reservation cleared.")

    async def cleanup(self):
        """Cleanup created resources."""
        self.print_section("CLEANUP")
        
        if self.order_id:
            print(f"Deleting Order: {self.order_id}")
            del_res = await self.client.delete(f"{self.base_url}/orders/{self.order_id}")
            if del_res.status_code == 204:
                print("✓ Order deleted successfully.")
            else:
                print(f"✗ Failed to delete Order {self.order_id}: {del_res.text}")

        if self.spu_id:
            print(f"Deleting SPU: {self.spu_id} (will cascade to SKU and Inventory)")
            del_res = await self.client.delete(f"{self.base_url}/spus/{self.spu_id}")
            if del_res.status_code == 204:
                print("✓ SPU Cleanup successful.")
            else:
                print(f"✗ Cleanup failed for SPU {self.spu_id}: {del_res.text}")

    async def run_test(self):
        """Run the full order workflow test."""
        self.print_section("ORDER WORKFLOW TEST")
        try:
            await self.setup_dependencies()
            await self.create_order()
            await self.read_order()
            await self.create_payment()
            await self.fulfill_order()
            await self.verify_inventory()
            self.print_section("✓✓✓ ORDER WORKFLOW TEST PASSED ✓✓✓")
        except Exception as e:
            print(f"\n\n{'=' * 70}")
            print(f"  ✗ ORDER WORKFLOW TEST FAILED!")
            print(f"{'=' * 70}")
            print(f"Error: {str(e)}")
        finally:
            await self.cleanup()


async def main():
    """Main entry point for the order workflow test."""
    async with OrderCrudTester() as tester:
        await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())