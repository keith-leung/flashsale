"""Unit tests for SKU CRUD operations."""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def test_spu():
    """Create a test SPU for SKU tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        slug = f"test-spu-{uuid.uuid4().hex[:8]}"
        spu_data = {"name": f"Test SPU {slug}", "slug": slug}
        response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = response.json()["data"]["id"]

        yield spu_id

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.fixture
def unique_sku_code():
    """Generate unique SKU code for each test."""
    return f"TEST-SKU-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_create_sku(test_spu, unique_sku_code):
    """Test creating a new SKU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        sku_data = {
            "sku_code": unique_sku_code,
            "name": f"Test SKU {unique_sku_code}",
            "spu_id": test_spu,
            "price": 99.99,
            "cost_price": 50.00,
            "track_inventory": True,
            "is_active": True,
            "initial_quantity": 100
        }

        response = await client.post("/api/v1/skus", json=sku_data)

        assert response.status_code == 201
        result = response.json()
        assert result["status"] == 201
        assert result["data"]["sku_code"] == unique_sku_code
        assert result["data"]["price"] == "99.99"
        assert "id" in result["data"]


@pytest.mark.asyncio
async def test_read_sku(test_spu, unique_sku_code):
    """Test reading a SKU by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SKU
        sku_data = {
            "sku_code": unique_sku_code,
            "name": f"Test SKU {unique_sku_code}",
            "spu_id": test_spu,
            "price": 99.99,
            "initial_quantity": 50
        }
        create_response = await client.post("/api/v1/skus", json=sku_data)
        sku_id = create_response.json()["data"]["id"]

        # Read SKU
        response = await client.get(f"/api/v1/skus/{sku_id}")

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["id"] == sku_id
        assert result["data"]["sku_code"] == unique_sku_code


@pytest.mark.asyncio
async def test_update_sku(test_spu, unique_sku_code):
    """Test updating a SKU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SKU
        sku_data = {
            "sku_code": unique_sku_code,
            "name": "Original Name",
            "spu_id": test_spu,
            "price": 99.99,
            "initial_quantity": 50
        }
        create_response = await client.post("/api/v1/skus", json=sku_data)
        sku_id = create_response.json()["data"]["id"]

        # Update SKU
        update_data = {
            "name": "Updated Name",
            "price": 129.99
        }
        response = await client.put(f"/api/v1/skus/{sku_id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["name"] == "Updated Name"
        assert result["data"]["price"] == "129.99"


@pytest.mark.asyncio
async def test_delete_sku(test_spu, unique_sku_code):
    """Test deleting a SKU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SKU
        sku_data = {
            "sku_code": unique_sku_code,
            "name": f"Test SKU {unique_sku_code}",
            "spu_id": test_spu,
            "price": 99.99,
            "initial_quantity": 50
        }
        create_response = await client.post("/api/v1/skus", json=sku_data)
        sku_id = create_response.json()["data"]["id"]

        # Delete SKU
        response = await client.delete(f"/api/v1/skus/{sku_id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/api/v1/skus/{sku_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_skus(test_spu, unique_sku_code):
    """Test listing SKUs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SKU
        sku_data = {
            "sku_code": unique_sku_code,
            "name": f"Test SKU {unique_sku_code}",
            "spu_id": test_spu,
            "price": 99.99,
            "initial_quantity": 50
        }
        await client.post("/api/v1/skus", json=sku_data)

        # List SKUs
        response = await client.get("/api/v1/skus")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result["data"], list)


@pytest.mark.asyncio
async def test_create_sku_with_nonexistent_spu(unique_sku_code):
    """Test creating SKU with non-existent SPU fails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        fake_spu_id = str(uuid.uuid4())
        sku_data = {
            "sku_code": unique_sku_code,
            "name": "Test SKU",
            "spu_id": fake_spu_id,
            "price": 99.99,
            "initial_quantity": 50
        }

        response = await client.post("/api/v1/skus", json=sku_data)
        assert response.status_code == 400
