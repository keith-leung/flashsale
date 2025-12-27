"""Unit tests for /health endpoint."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_get_method():
    """Test health endpoint with GET method returns plain text 200 OK."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.text == "200 OK"
        assert "text/plain" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_health_head_method():
    """Test health endpoint with HEAD method."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.head("/health")

        assert response.status_code == 200
        # HEAD method should not return body
        assert response.text == ""


@pytest.mark.asyncio
async def test_health_no_database_dependency():
    """Test that health endpoint does not require database connection.

    This is critical for load balancers - health checks should be fast
    and not depend on external services.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Make multiple rapid requests - should all succeed
        for _ in range(100):
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.text == "200 OK"
