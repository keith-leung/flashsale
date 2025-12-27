"""Unit tests for SPU CRUD operations."""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def unique_slug():
    """Generate unique slug for each test."""
    return f"test-spu-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_create_spu(unique_slug):
    """Test creating a new SPU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        spu_data = {
            "name": f"Test SPU {unique_slug}",
            "slug": unique_slug,
            "description": "Test SPU for unit tests",
            "is_active": True,
        }

        response = await client.post("/api/v1/spus", json=spu_data)

        assert response.status_code == 201
        result = response.json()
        assert result["status"] == 201
        assert "data" in result
        assert result["data"]["name"] == spu_data["name"]
        assert result["data"]["slug"] == unique_slug
        assert "id" in result["data"]

        # Cleanup
        spu_id = result["data"]["id"]
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_read_spu(unique_slug):
    """Test reading a SPU by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SPU first
        spu_data = {"name": f"Test SPU {unique_slug}", "slug": unique_slug}
        create_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = create_response.json()["data"]["id"]

        # Read SPU
        response = await client.get(f"/api/v1/spus/{spu_id}")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == 200
        assert result["data"]["id"] == spu_id
        assert result["data"]["slug"] == unique_slug

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_update_spu(unique_slug):
    """Test updating a SPU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SPU
        spu_data = {"name": f"Test SPU {unique_slug}", "slug": unique_slug}
        create_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = create_response.json()["data"]["id"]

        # Update SPU
        update_data = {
            "name": f"Updated Test SPU {unique_slug}",
            "description": "Updated description"
        }
        response = await client.put(f"/api/v1/spus/{spu_id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["name"] == update_data["name"]
        assert result["data"]["description"] == update_data["description"]

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_delete_spu(unique_slug):
    """Test deleting a SPU."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SPU
        spu_data = {"name": f"Test SPU {unique_slug}", "slug": unique_slug}
        create_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = create_response.json()["data"]["id"]

        # Delete SPU
        response = await client.delete(f"/api/v1/spus/{spu_id}")

        assert response.status_code == 204

        # Verify deletion - should get 404
        get_response = await client.get(f"/api/v1/spus/{spu_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_spus(unique_slug):
    """Test listing SPUs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create test SPU
        spu_data = {"name": f"Test SPU {unique_slug}", "slug": unique_slug}
        create_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = create_response.json()["data"]["id"]

        # List SPUs
        response = await client.get("/api/v1/spus")

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == 200
        assert "data" in result
        assert isinstance(result["data"], list)

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_create_spu_duplicate_slug(unique_slug):
    """Test creating SPU with duplicate slug fails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        spu_data = {"name": f"Test SPU {unique_slug}", "slug": unique_slug}

        # Create first SPU
        response1 = await client.post("/api/v1/spus", json=spu_data)
        assert response1.status_code == 201
        spu_id = response1.json()["data"]["id"]

        # Try to create duplicate
        response2 = await client.post("/api/v1/spus", json=spu_data)
        assert response2.status_code == 400

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")
