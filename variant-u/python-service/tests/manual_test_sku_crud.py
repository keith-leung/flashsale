"""
Test script for SKU (Stock Keeping Unit) CRUD operations.
"""

import asyncio
import httpx
from typing import Dict, Any
import json
import uuid

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"


class SKUCrudTester:
    """SKU CRUD operations tester"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
        self.test_run_id = uuid.uuid4().hex[:8]
        self.spu_id = None
        self.sku_id = None
        self.spu_slug = f"test-spu-for-sku-{self.test_run_id}"
        self.sku_code = f"TEST-SKU-{self.test_run_id}"

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    def print_section(self, title: str):
        """Print section header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_response(self, response: httpx.Response):
        """Print HTTP response details"""
        print(f"Status: {response.status_code}")
        if response.status_code >= 400:
            print(f"Error: {response.text}")
        else:
            try:
                print(json.dumps(response.json(), indent=2, default=str))
            except json.JSONDecodeError:
                print(response.text)

    async def setup_spu(self) -> str:
        """Create a prerequisite SPU."""
        self.print_section("SETUP: Create prerequisite SPU")
        spu_data = {
            "name": f"Test SPU for SKU {self.test_run_id}",
            "slug": self.spu_slug,
            "description": "A test SPU for SKU CRUD operations.",
            "is_active": True,
        }
        response = await self.client.post(f"{self.base_url}/spus", json=spu_data)
        if response.status_code == 201:
            result = response.json()
            self.spu_id = result["data"]["id"]
            print(f"✓ Prerequisite SPU created. ID: {self.spu_id}")
            return self.spu_id
        else:
            raise Exception(f"Failed to create prerequisite SPU: {response.text}")

    async def create_sku(self):
        """Create a new SKU."""
        self.print_section("CREATE SKU")
        sku_data = {
            "sku_code": self.sku_code,
            "name": f"Test SKU {self.test_run_id}",
            "spu_id": self.spu_id,
            "price": 99.99,
            "is_active": True,
        }
        print(f"POST {self.base_url}/skus")
        print(f"Request: {json.dumps(sku_data, indent=2, default=str)}")
        response = await self.client.post(f"{self.base_url}/skus", json=sku_data)
        self.print_response(response)
        if response.status_code == 201:
            result = response.json()
            self.sku_id = result["data"]["id"]
            print(f"\n✓ SKU Created Successfully! ID: {self.sku_id}")
        else:
            raise Exception(f"Failed to create SKU: {response.text}")

    async def read_sku(self):
        """Read the created SKU."""
        self.print_section("READ SKU")
        print(f"GET {self.base_url}/skus/{self.sku_id}")
        response = await self.client.get(f"{self.base_url}/skus/{self.sku_id}")
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to read SKU: {response.text}")
        print(f"\n✓ SKU Read Successfully!")

    async def update_sku(self):
        """Update the SKU."""
        self.print_section("UPDATE SKU")
        update_data = {"name": "Updated Test SKU", "price": 129.99}
        print(f"PUT {self.base_url}/skus/{self.sku_id}")
        print(f"Request: {json.dumps(update_data, indent=2)}")
        response = await self.client.put(
            f"{self.base_url}/skus/{self.sku_id}", json=update_data
        )
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to update SKU: {response.text}")
        print(f"\n✓ SKU Updated Successfully!")

    async def delete_sku(self):
        """Delete the SKU."""
        self.print_section("DELETE SKU")
        print(f"DELETE {self.base_url}/skus/{self.sku_id}")
        response = await self.client.delete(f"{self.base_url}/skus/{self.sku_id}")
        print(f"Status: {response.status_code}")
        if response.status_code != 204:
            raise Exception(f"Failed to delete SKU: {response.text}")
        print(f"\n✓ SKU Deleted Successfully!")

    async def verify_sku_deleted(self):
        """Verify that the SKU has been deleted."""
        self.print_section("VERIFY SKU DELETION")
        print(f"GET {self.base_url}/skus/{self.sku_id}")
        response = await self.client.get(f"{self.base_url}/skus/{self.sku_id}")
        self.print_response(response)
        if response.status_code == 404:
            print(f"\n✓ SKU correctly reported as not found (404).")
        else:
            raise Exception(f"SKU was not deleted successfully: {response.text}")

    async def cleanup_spu(self):
        """Delete the prerequisite SPU."""
        self.print_section("CLEANUP: Delete SPU")
        if self.spu_id:
            print(f"DELETE {self.base_url}/spus/{self.spu_id}")
            response = await self.client.delete(f"{self.base_url}/spus/{self.spu_id}")
            if response.status_code == 204:
                print(f"✓ Prerequisite SPU deleted successfully.")
            else:
                print(f"✗ Failed to delete prerequisite SPU: {response.text}")

    async def run_test(self):
        """Run the full SKU CRUD test."""
        self.print_section("SKU CRUD TEST")
        try:
            await self.setup_spu()
            await self.create_sku()
            await self.read_sku()
            await self.update_sku()
            await self.read_sku()  # Read again to verify update
            await self.delete_sku()
            await self.verify_sku_deleted()
            self.print_section("✓✓✓ SKU CRUD TEST PASSED ✓✓✓")
        except Exception as e:
            print(f"\n\n{"=" * 70}")
            print(f"  ✗ SKU CRUD TEST FAILED!")
            print(f"{ "=" * 70}")
            print(f"Error: {str(e)}")
        finally:
            await self.cleanup_spu()


async def main():
    """Main entry point for the SKU CRUD test."""
    async with SKUCrudTester() as tester:
        await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())