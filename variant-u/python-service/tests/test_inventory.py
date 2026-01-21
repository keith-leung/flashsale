"""Unit tests for Inventory management operations."""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def test_sku_with_inventory():
    """Create a test SKU with inventory."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SPU
        slug = f"test-spu-{uuid.uuid4().hex[:8]}"
        spu_data = {"name": f"Test SPU {slug}", "slug": slug}
        spu_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = spu_response.json()["data"]["id"]

        # Create SKU with inventory
        sku_code = f"TEST-SKU-{uuid.uuid4().hex[:8]}"
        sku_data = {
            "sku_code": sku_code,
            "name": f"Test SKU {sku_code}",
            "spu_id": spu_id,
            "price": 100.00,
            "initial_quantity": 100
        }
        sku_response = await client.post("/api/v1/skus", json=sku_data)
        sku_id = sku_response.json()["data"]["id"]

        yield sku_id

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_get_inventory(test_sku_with_inventory):
    """Test getting inventory for a SKU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/inventory/{test_sku_with_inventory}")

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["sku_id"] == test_sku_with_inventory
        assert result["data"]["quantity"] == 100
        assert result["data"]["reserved_quantity"] == 0
        assert result["data"]["available_quantity"] == 100


@pytest.mark.asyncio
async def test_update_inventory(test_sku_with_inventory):
    """Test updating inventory quantity."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        update_data = {
            "quantity": 200,
            "allow_negative_stock": False
        }

        response = await client.put(
            f"/api/v1/inventory/{test_sku_with_inventory}",
            json=update_data
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["quantity"] == 200


@pytest.mark.asyncio
async def test_adjust_inventory(test_sku_with_inventory):
    """Test adjusting inventory with positive and negative values."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Adjust by +50
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/adjust?adjustment=50"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["quantity"] == 150

        # Adjust by -30
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/adjust?adjustment=-30"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["quantity"] == 120


@pytest.mark.asyncio
async def test_reserve_inventory(test_sku_with_inventory):
    """Test reserving inventory quantity."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/reserve?quantity=20"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["reserved_quantity"] == 20
        assert result["data"]["available_quantity"] == 80


@pytest.mark.asyncio
async def test_release_inventory(test_sku_with_inventory):
    """Test releasing reserved inventory."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Reserve first
        await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/reserve?quantity=30"
        )

        # Release
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/release?quantity=10"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["reserved_quantity"] == 20
        assert result["data"]["available_quantity"] == 80


@pytest.mark.asyncio
async def test_reserve_more_than_available(test_sku_with_inventory):
    """Test reserving more than available quantity fails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/reserve?quantity=200"
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_adjust_to_negative_without_flag(test_sku_with_inventory):
    """Test adjusting to negative without allow_negative_stock fails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/inventory/{test_sku_with_inventory}/adjust?adjustment=-200"
        )

        assert response.status_code == 400
