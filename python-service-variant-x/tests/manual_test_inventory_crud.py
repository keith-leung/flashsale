"""
Test script for Inventory CRUD and management operations.
"""

import asyncio
import httpx
import json
import uuid

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"


class InventoryCrudTester:
    """Inventory operations tester"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
        self.test_run_id = uuid.uuid4().hex[:8]
        self.spu_id = None
        self.sku_id = None
        self.spu_slug = f"test-spu-for-inv-{self.test_run_id}"
        self.sku_code = f"TEST-INV-SKU-{self.test_run_id}"

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

    async def setup_sku(self):
        """Create prerequisite SPU and SKU."""
        self.print_section("SETUP: Create SPU and SKU")
        # Create SPU
        spu_data = {"name": f"Test SPU for Inventory {self.test_run_id}", "slug": self.spu_slug}
        spu_res = await self.client.post(f"{self.base_url}/spus", json=spu_data)
        if spu_res.status_code != 201:
            raise Exception(f"Setup failed: Could not create SPU. {spu_res.text}")
        self.spu_id = spu_res.json()["data"]["id"]
        print(f"✓ Prerequisite SPU created. ID: {self.spu_id}")

        # Create SKU
        sku_data = {
            "sku_code": self.sku_code,
            "name": f"Test SKU for Inventory {self.test_run_id}",
            "spu_id": self.spu_id,
            "price": 100.00,
            "initial_quantity": 50
        }
        sku_res = await self.client.post(f"{self.base_url}/skus", json=sku_data)
        if sku_res.status_code != 201:
            raise Exception(f"Setup failed: Could not create SKU. {sku_res.text}")
        self.sku_id = sku_res.json()["data"]["id"]
        print(f"✓ Prerequisite SKU created. ID: {self.sku_id}")
        print(f"  Initial inventory should be 50.")

    async def get_inventory(self):
        """Get inventory for the SKU."""
        self.print_section("GET INVENTORY")
        print(f"GET {self.base_url}/inventory/{self.sku_id}")
        response = await self.client.get(f"{self.base_url}/inventory/{self.sku_id}")
        self.print_response(response)
        if response.status_code != 200 or response.json()["data"]["quantity"] != 50:
            raise Exception("Failed to get correct initial inventory.")
        print("\n✓ Initial inventory is correct (50).")

    async def update_inventory(self):
        """Update inventory for the SKU."""
        self.print_section("UPDATE INVENTORY")
        update_data = {"quantity": 200, "allow_negative_stock": True}
        print(f"PUT {self.base_url}/inventory/{self.sku_id}")
        print(f"Request: {json.dumps(update_data, indent=2)}")
        response = await self.client.put(f"{self.base_url}/inventory/{self.sku_id}", json=update_data)
        self.print_response(response)
        if response.status_code != 200 or response.json()["data"]["quantity"] != 200:
            raise Exception(f"Failed to update inventory: {response.text}")
        print("\n✓ Inventory updated successfully to 200.")

    async def adjust_inventory(self):
        """Adjust inventory quantity."""
        self.print_section("ADJUST INVENTORY")
        # Adjust by -30
        print("Adjusting quantity by -30...")
        adj_res = await self.client.post(f"{self.base_url}/inventory/{self.sku_id}/adjust?adjustment=-30")
        self.print_response(adj_res)
        if adj_res.status_code != 200 or adj_res.json()["data"]["quantity"] != 170:
            raise Exception("Failed to adjust inventory.")
        print("\n✓ Inventory adjusted successfully to 170.")

    async def reserve_and_release_inventory(self):
        """Reserve and then release inventory."""
        self.print_section("RESERVE AND RELEASE INVENTORY")
        # Reserve 20
        print("Reserving quantity of 20...")
        res_res = await self.client.post(f"{self.base_url}/inventory/{self.sku_id}/reserve?quantity=20")
        self.print_response(res_res)
        if res_res.status_code != 200 or res_res.json()["data"]["reserved_quantity"] != 20:
            raise Exception(f"Failed to reserve inventory: {res_res.text}")
        print("\n✓ Inventory reserved successfully (20). Available should be 150.")

        # Release 10
        print("\nReleasing quantity of 10...")
        rel_res = await self.client.post(f"{self.base_url}/inventory/{self.sku_id}/release?quantity=10")
        self.print_response(rel_res)
        if rel_res.status_code != 200 or rel_res.json()["data"]["reserved_quantity"] != 10:
            raise Exception(f"Failed to release inventory: {rel_res.text}")
        print("\n✓ Inventory released successfully (10). Reserved is now 10, available is 160.")


    async def cleanup(self):
        """Cleanup created resources."""
        self.print_section("CLEANUP")
        if self.spu_id:
            print(f"Deleting SPU: {self.spu_id} (will cascade to SKU and Inventory)")
            del_res = await self.client.delete(f"{self.base_url}/spus/{self.spu_id}")
            if del_res.status_code == 204:
                print("✓ Cleanup successful.")
            else:
                print(f"✗ Cleanup failed for SPU {self.spu_id}: {del_res.text}")

    async def run_test(self):
        """Run the full inventory management test."""
        self.print_section("INVENTORY MANAGEMENT TEST")
        try:
            await self.setup_sku()
            await self.get_inventory()
            await self.update_inventory()
            await self.adjust_inventory()
            await self.reserve_and_release_inventory()
            self.print_section("✓✓✓ INVENTORY TEST PASSED ✓✓✓")
        except Exception as e:
            print(f"\n\n{'=' * 70}")
            print(f"  ✗ INVENTORY TEST FAILED!")
            print(f"{'=' * 70}")
            print(f"Error: {str(e)}")
        finally:
            await self.cleanup()


async def main():
    """Main entry point for the inventory test."""
    async with InventoryCrudTester() as tester:
        await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())