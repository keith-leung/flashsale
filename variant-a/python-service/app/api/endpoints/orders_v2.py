"""
CORRECTED Order Creation Endpoint for Variant A

Key Changes:
1. ❌ REMOVED: Campaign-level Redis check on every request (line 271)
2. ✅ ADDED: Direct use of AdaptiveInventoryManager (local memory first)
3. ✅ ADDED: Three-tier stock hierarchy: local → Redis campaign pool → ordinary stock
4. ✅ ADDED: Price tracking to stop benchmark when falling back to ordinary

This is the reference implementation demonstrating correct Variant A architecture.
"""

import time
import uuid
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.order import OrderCreate, OrderResponse
from app.schemas.response import ResponseDTO
from app.services.adaptive_inventory_v2 import AdaptiveInventoryManager
from app.models.order import Order, OrderLineItem, OrderStatus
import logging

logger = logging.getLogger(__name__)


async def create_order_variant_a_corrected(
    order_data: OrderCreate,
    order_number: str,
    flash_sale_id: str,
    sku_metadata: dict,
    adaptive_manager: AdaptiveInventoryManager,
    background_tasks: BackgroundTasks,
    db: AsyncSession
) -> ResponseDTO[OrderResponse]:
    """
    Corrected Variant A: Pure local memory with producer-consumer pattern

    Flow:
    1. Reserve from local memory (99%+ of requests - pure RAM)
    2. If local depleted, try Redis campaign pool (dual stock)
    3. If campaign pool depleted, fall back to ordinary stock
    4. Return price_type to indicate which stock was used

    NO campaign-level Redis check!
    """
    start_time = time.perf_counter()

    logger.info(
        f"[VARIANT A CORRECTED] Order {order_number}, "
        f"campaign {flash_sale_id}"
    )

    # Extract info
    customer_email = order_data.customer_email
    customer_name = order_data.customer_name or "Unknown"

    # Track reservation results
    reserved_items = []  # [(sku_id, quantity, price_type, price)]
    total_amount = 0.0
    fell_back_to_ordinary = False

    try:
        # Reserve each line item
        for item_data in order_data.line_items:
            sku_id = str(item_data.sku_id)
            quantity = item_data.quantity

            # Reserve items one by one
            for _ in range(quantity):
                # Use adaptive inventory manager (local → campaign pool → ordinary)
                success, price_type, price = await adaptive_manager.reserve_item(sku_id)

                if not success:
                    # Completely sold out
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"SKU {sku_id} completely sold out"
                    )

                # Track what stock was used
                if price_type == 'ordinary':
                    fell_back_to_ordinary = True
                    logger.warning(
                        f"[BENCHMARK STOP INDICATOR] Order {order_number} "
                        f"using ordinary stock (price={price}). "
                        f"Campaign exhausted in this service."
                    )

                total_amount += price

            reserved_items.append((sku_id, quantity, price_type, price))

        # Queue order for async persistence (like old implementation)
        from app.core.redis_cache import redis_cache

        order_payload = {
            "order_number": order_number,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "flash_sale_id": flash_sale_id,
            "line_items": [
                {
                    "sku_id": sku_id,
                    "quantity": quantity,
                    "unit_price": str(unit_price),
                    "price_type": price_type
                }
                for sku_id, quantity, price_type, unit_price in reserved_items
            ],
            "total_amount": str(total_amount),
            "fell_back_to_ordinary": fell_back_to_ordinary
        }

        await redis_cache.queue_order(order_payload)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[VARIANT A CORRECTED] Order {order_number} reserved successfully, "
            f"queued for persistence, duration={duration_ms:.2f}ms, "
            f"fell_back_to_ordinary={fell_back_to_ordinary}"
        )

        # Build immediate response (temporary ID)
        from datetime import datetime
        from decimal import Decimal

        temp_order_id = str(uuid.uuid4())

        order_dict = {
            'id': temp_order_id,
            'order_number': order_number,
            'customer_email': customer_email,
            'customer_name': customer_name,
            'subtotal': str(total_amount),
            'tax_amount': '0.0',
            'shipping_amount': '0.0',
            'total_amount': str(total_amount),
            'currency': order_data.currency or "USD",
            'status': 'pending',
            'notes': None,
            'flash_sale_campaign_id': flash_sale_id if not fell_back_to_ordinary else None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'line_items': []
        }

        return ResponseDTO(
            status=201,
            message="Order reserved successfully (Variant A Corrected)",
            data=order_dict
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Order creation failed: {e}", exc_info=True)

        # Rollback is automatic with async session

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )
