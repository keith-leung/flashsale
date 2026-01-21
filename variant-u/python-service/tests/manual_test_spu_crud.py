"""
Test script for SPU (Standard Product Unit) CRUD operations.
"""

import asyncio
import httpx
from typing import Dict, Any
import json
import uuid

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"


class SPUCrudTester:
    """SPU CRUD operations tester"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = None
        self.test_run_id = uuid.uuid4().hex[:8]
        self.spu_id = None
        self.spu_slug = f"test-spu-{self.test_run_id}"

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
                data = response.json()
                print(json.dumps(data, indent=2, default=str))
            except:
                print(response.text)

    async def create_spu(self) -> Dict[str, Any]:
        """Create a new SPU."""
        self.print_section("CREATE SPU")
        spu_data = {
            "name": f"Test SPU {self.test_run_id}",
            "slug": self.spu_slug,
            "description": "A test SPU for CRUD operations.",
            "is_active": True,
        }
        print(f"POST {self.base_url}/spus")
        print(f"Request: {json.dumps(spu_data, indent=2)}")
        response = await self.client.post(f"{self.base_url}/spus", json=spu_data)
        self.print_response(response)
        if response.status_code == 201:
            result = response.json()
            self.spu_id = result["data"]["id"]
            print(f"\n✓ SPU Created Successfully! ID: {self.spu_id}")
            return result["data"]
        else:
            raise Exception(f"Failed to create SPU: {response.text}")

    async def read_spu(self):
        """Read the created SPU."""
        self.print_section("READ SPU")
        print(f"GET {self.base_url}/spus/{self.spu_id}")
        response = await self.client.get(f"{self.base_url}/spus/{self.spu_id}")
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to read SPU: {response.text}")
        print(f"\n✓ SPU Read Successfully!")

    async def update_spu(self):
        """Update the SPU."""
        self.print_section("UPDATE SPU")
        update_data = {
            "name": f"Updated Test SPU {self.test_run_id}",
            "description": "This SPU has been updated.",
        }
        print(f"PUT {self.base_url}/spus/{self.spu_id}")
        print(f"Request: {json.dumps(update_data, indent=2)}")
        response = await self.client.put(
            f"{self.base_url}/spus/{self.spu_id}", json=update_data
        )
        self.print_response(response)
        if response.status_code != 200:
            raise Exception(f"Failed to update SPU: {response.text}")
        print(f"\n✓ SPU Updated Successfully!")

    async def delete_spu(self):
        """Delete the SPU."""
        self.print_section("DELETE SPU")
        print(f"DELETE {self.base_url}/spus/{self.spu_id}")
        response = await self.client.delete(f"{self.base_url}/spus/{self.spu_id}")
        print(f"Status: {response.status_code}")
        if response.status_code != 204:
            raise Exception(f"Failed to delete SPU: {response.text}")
        print(f"\n✓ SPU Deleted Successfully!")

    async def verify_spu_deleted(self):
        """Verify that the SPU has been deleted."""
        self.print_section("VERIFY SPU DELETION")
        print(f"GET {self.base_url}/spus/{self.spu_id}")
        response = await self.client.get(f"{self.base_url}/spus/{self.spu_id}")
        self.print_response(response)
        if response.status_code == 404:
            print(f"\n✓ SPU correctly reported as not found (404).")
        else:
            raise Exception("SPU was not deleted successfully.")

    async def run_test(self):
        """Run the full SPU CRUD test."""
        self.print_section("SPU CRUD TEST")
        try:
            await self.create_spu()
            await self.read_spu()
            await self.update_spu()
            await self.read_spu()  # Read again to verify update
            await self.delete_spu()
            await self.verify_spu_deleted()
            self.print_section("✓✓✓ SPU CRUD TEST PASSED ✓✓✓")
        except Exception as e:
            print(f"\n\n{'=' * 70}")
            print(f"  ✗ SPU CRUD TEST FAILED!")
            print(f"{'=' * 70}")
            print(f"Error: {str(e)}")
            # No cleanup needed if creation failed or deletion was the goal
            if self.spu_id:
                print("Attempting to cleanup created SPU...")
                try:
                    await self.delete_spu()
                except Exception as cleanup_e:
                    print(f"Cleanup failed: {cleanup_e}")


async def main():
    """Main entry point for the SPU CRUD test."""
    async with SPUCrudTester() as tester:
        await tester.run_test()


if __name__ == "__main__":
    asyncio.run(main())