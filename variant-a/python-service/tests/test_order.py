"""Unit tests for Order workflow operations."""

import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def test_sku_for_order():
    """Create a test SKU for order tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create SPU
        slug = f"test-spu-{uuid.uuid4().hex[:8]}"
        spu_data = {"name": f"Test SPU {slug}", "slug": slug}
        spu_response = await client.post("/api/v1/spus", json=spu_data)
        spu_id = spu_response.json()["data"]["id"]

        # Create SKU
        sku_code = f"TEST-SKU-{uuid.uuid4().hex[:8]}"
        sku_data = {
            "sku_code": sku_code,
            "name": f"Test SKU {sku_code}",
            "spu_id": spu_id,
            "price": 250.00,
            "initial_quantity": 100
        }
        sku_response = await client.post("/api/v1/skus", json=sku_data)
        sku_id = sku_response.json()["data"]["id"]

        yield {"sku_id": sku_id, "spu_id": spu_id}

        # Cleanup
        await client.delete(f"/api/v1/spus/{spu_id}")


@pytest.mark.asyncio
async def test_create_order(test_sku_for_order):
    """Test creating a new order."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [
                {
                    "sku_id": test_sku_for_order["sku_id"],
                    "quantity": 2
                }
            ]
        }

        response = await client.post("/api/v1/orders", json=order_data)

        assert response.status_code == 201
        result = response.json()
        assert result["status"] == 201
        assert result["data"]["customer_email"] == order_data["customer_email"]
        assert result["data"]["status"] == "pending"
        assert len(result["data"]["line_items"]) == 1
        assert result["data"]["total_amount"] == "500.00"

        # Cleanup
        order_id = result["data"]["id"]
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_read_order(test_sku_for_order):
    """Test reading an order by ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create order
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 1}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # Read order
        response = await client.get(f"/api/v1/orders/{order_id}")

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["id"] == order_id
        assert len(result["data"]["line_items"]) == 1

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_update_order(test_sku_for_order):
    """Test updating an order."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create order
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Original Name",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 1}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # Update order
        update_data = {"customer_name": "Updated Name"}
        response = await client.put(f"/api/v1/orders/{order_id}", json=update_data)

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["customer_name"] == "Updated Name"

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_create_payment_for_order(test_sku_for_order):
    """Test creating a payment for an order."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create order
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 2}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # Create payment
        payment_data = {
            "amount": 500.00,
            "currency": "USD",
            "payment_method": "credit_card"
        }
        response = await client.post(
            f"/api/v1/orders/{order_id}/payments",
            json=payment_data
        )

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["order_id"] == order_id
        assert result["data"]["status"] == "captured"

        # Verify order status changed to confirmed
        order_response = await client.get(f"/api/v1/orders/{order_id}")
        assert order_response.json()["data"]["status"] == "confirmed"

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_fulfill_order(test_sku_for_order):
    """Test fulfilling an order."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create and pay for order
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 3}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # Create payment
        payment_data = {"amount": 750.00, "currency": "USD", "payment_method": "credit_card"}
        await client.post(f"/api/v1/orders/{order_id}/payments", json=payment_data)

        # Get initial inventory
        inv_before = await client.get(f"/api/v1/inventory/{test_sku_for_order['sku_id']}")
        initial_qty = inv_before.json()["data"]["quantity"]

        # Fulfill order
        response = await client.post(f"/api/v1/orders/{order_id}/fulfill")

        assert response.status_code == 200
        result = response.json()
        assert result["data"]["status"] == "shipped"

        # Verify inventory decreased
        inv_after = await client.get(f"/api/v1/inventory/{test_sku_for_order['sku_id']}")
        final_qty = inv_after.json()["data"]["quantity"]
        assert final_qty == initial_qty - 3

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_list_orders(test_sku_for_order):
    """Test listing orders."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create order
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 1}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # List orders
        response = await client.get("/api/v1/orders")

        assert response.status_code == 200
        result = response.json()
        assert isinstance(result["data"], list)

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")


@pytest.mark.asyncio
async def test_fulfill_order_without_payment_fails(test_sku_for_order):
    """Test that fulfilling order without payment fails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create order (no payment)
        order_data = {
            "customer_email": f"test-{uuid.uuid4().hex[:8]}@example.com",
            "customer_name": "Test Customer",
            "currency": "USD",
            "line_items": [{"sku_id": test_sku_for_order["sku_id"], "quantity": 1}]
        }
        create_response = await client.post("/api/v1/orders", json=order_data)
        order_id = create_response.json()["data"]["id"]

        # Try to fulfill without payment
        response = await client.post(f"/api/v1/orders/{order_id}/fulfill")

        assert response.status_code == 400

        # Cleanup
        await client.delete(f"/api/v1/orders/{order_id}")
