"""
Variant A FIXED - Order Creation with Correct Dual-Layer Tracking

This implements the CORRECT business logic:
- Layer 1: SPU-level campaign counter (shared across ALL SKUs)
- Layer 2: SKU-level inventory caches (per individual SKU)

Fixes the flaw: No longer conflates SPU and SKU into single counter.
"""

import time
import uuid
import logging
from typing import Optional
from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.order import OrderCreate
from app.schemas.response import ResponseDTO
from app.services.campaign_memory_allocator import CampaignMemoryAllocator
from app.core.redis_cache import redis_cache

logger = logging.getLogger(__name__)


async def create_order_variant_a_fixed(
    order_data: OrderCreate,
    order_number: str,
    flash_sale_id: str,
    sku_metadata: dict,
    allocator: CampaignMemoryAllocator,
    background_tasks: BackgroundTasks,
    db: AsyncSession
) -> ResponseDTO:
    """
    Create order using FIXED dual-layer tracking

    Flow:
    1. Reserve from SPU counter (campaign-level limit)
    2. Reserve from SKU cache (SKU-level inventory)
    3. Both must succeed for order to proceed
    4. Queue order for async persistence

    Args:
        order_data: Order request data
        order_number: Generated order number
        flash_sale_id: Campaign ID
        sku_metadata: SKU metadata from Redis
        allocator: Campaign memory allocator instance
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        ResponseDTO with order response
    """
    start_time = time.perf_counter()

    logger.info(
        f"[VARIANT A FIXED] Order {order_number}, campaign {flash_sale_id}"
    )

    # Extract info
    customer_email = order_data.customer_email
    customer_name = order_data.customer_name or "Unknown"

    # Track reservations
    reserved_items = []  # [(sku_id, quantity, price_type, price)]
    total_amount = 0.0
    used_ordinary_price = False

    try:
        # Reserve each line item
        for item_data in order_data.line_items:
            sku_id = str(item_data.sku_id)
            quantity = item_data.quantity

            # Reserve items one by one (dual-layer check)
            for _ in range(quantity):
                success, price_type, price = await allocator.reserve_item(
                    campaign_id=flash_sale_id,
                    sku_id=sku_id
                )

                if not success:
                    if price_type == "ordinary":
                        # Campaign exhausted, switched to ordinary pricing
                        used_ordinary_price = True

                        logger.warning(
                            f"[BENCHMARK STOP] Order {order_number} hit campaign limit, "
                            f"using ordinary price. TEST SHOULD STOP."
                        )

                        # For benchmarking: Fail the order to stop test
                        # In production: Would continue with ordinary price
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Flash sale campaign exhausted (benchmark stop indicator)"
                        )
                    else:
                        # Completely sold out
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"SKU {sku_id} sold out"
                        )

                # Add to total
                total_amount += price

            reserved_items.append((sku_id, quantity, price_type, price))

        # FIRE-AND-FORGET: Queue to local buffer (zero blocking)
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
                }
                for sku_id, quantity, price_type, unit_price in reserved_items
            ],
            "total_amount": str(total_amount),
            "created_at": int(time.time() * 1000)
        }

        await allocator.queue_order_fire_and_forget(order_payload)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"[VARIANT A FIXED] Order {order_number} reserved, "
            f"queued for persistence, duration={duration_ms:.2f}ms"
        )

        # Build immediate response
        from datetime import datetime

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
            'flash_sale_campaign_id': flash_sale_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'line_items': []
        }

        return ResponseDTO(
            status=201,
            message="Order reserved successfully (Variant A FIXED - Dual-Layer)",
            data=order_dict
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Order creation failed: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order creation failed: {str(e)}"
        )
