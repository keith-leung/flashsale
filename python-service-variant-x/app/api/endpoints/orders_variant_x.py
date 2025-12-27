"""
Variant X Order Creation Endpoint - Redis-Only Architecture

Key optimizations:
1. Cache-aside pattern for SKU reads
2. Batch prefetch SKUs from Redis using pipeline
3. Reduce database roundtrips from N+1 to approximately 1-2
4. Aggressive Redis caching with appropriate TTLs
"""

import logging
from typing import List, Dict, Any
from decimal import Decimal

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.id_generator import generate_id
from app.core.redis_cache import cache
from app.models.order import Order, OrderLineItem
from app.models.sku import SKU
from app.schemas.order import OrderCreate, OrderResponse
from app.schemas.response import ResponseDTO

logger = logging.getLogger(__name__)


def serialize_sku_for_cache(sku: SKU) -> Dict[str, Any]:
    """Serialize SKU object for Redis caching."""
    return {
        "id": sku.id,
        "sku_code": sku.sku_code,
        "name": sku.name,
        "price": float(sku.price),
        "track_inventory": sku.track_inventory,
        "spu_name": getattr(sku.spu, 'name', None) if sku.spu else None,
        "inventory": {
            "id": sku.inventory.id,
            "sku_id": sku.inventory.sku_id,
            "quantity": sku.inventory.quantity,
            "reserved_quantity": sku.inventory.reserved_quantity,
            "available_quantity": sku.inventory.available_quantity,
        } if sku.inventory else None
    }


async def get_sku_with_cache(sku_id: str, db: AsyncSession) -> tuple[SKU, Dict[str, Any]]:
    """
    Get SKU from cache or database using cache-aside pattern.

    Returns:
        Tuple of (SKU object, cached data dict)
    """
    # Try cache first
    cached_data = await cache.get_sku(sku_id)

    if cached_data:
        # Cache hit - still need to load from DB for inventory reservation
        # but we can skip validation checks
        result = await db.execute(
            select(SKU).options(
                selectinload(SKU.inventory),
                selectinload(SKU.spu)
            ).filter(SKU.id == sku_id)
        )
        sku = result.scalar_one_or_none()

        if not sku:
            # Cache is stale, invalidate
            await cache.invalidate_sku(sku_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU {sku_id} not found")

        return sku, cached_data

    # Cache miss - load from database
    result = await db.execute(
        select(SKU).options(
            selectinload(SKU.inventory),
            selectinload(SKU.spu)
        ).filter(SKU.id == sku_id)
    )
    sku = result.scalar_one_or_none()

    if not sku:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU {sku_id} not found")

    # Cache for future requests
    cached_data = serialize_sku_for_cache(sku)
    await cache.set_sku(sku_id, cached_data)

    return sku, cached_data


async def create_order_variant_x(order_data: OrderCreate, db: AsyncSession) -> ResponseDTO[OrderResponse]:
    """
    Variant X: Redis-optimized order creation.

    Performance optimizations:
    1. Batch prefetch all SKU IDs from Redis (single pipeline operation)
    2. For cache misses, batch load from database
    3. Update Redis cache for future requests
    4. Minimize database roundtrips
    """
    order_number = f"ORD-{generate_id()}"
    logger.info(
        "Starting order creation (Variant X)",
        extra={
            "order_number": order_number,
            "customer_email": order_data.customer_email,
            "variant": "X",
        },
    )

    try:
        # Step 1: Extract SKU IDs
        sku_ids = [str(item.sku_id) for item in order_data.line_items]
        logger.debug(f"Fetching SKU data for {len(sku_ids)} items")

        # Step 2: Batch prefetch from Redis (single pipeline operation)
        cached_skus = await cache.get_multi_sku(sku_ids)
        cache_hits = sum(1 for v in cached_skus.values() if v is not None)
        cache_misses = len(sku_ids) - cache_hits

        logger.info(
            f"Redis cache performance: {cache_hits} hits, {cache_misses} misses",
            extra={
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "hit_rate": f"{(cache_hits / len(sku_ids) * 100):.1f}%" if sku_ids else "0%"
            }
        )

        # Step 3: Load cache misses from database (single query if possible)
        sku_objects = {}
        if cache_misses > 0:
            missing_ids = [sku_id for sku_id, data in cached_skus.items() if data is None]
            result = await db.execute(
                select(SKU).options(
                    selectinload(SKU.inventory),
                    selectinload(SKU.spu)
                ).filter(SKU.id.in_(missing_ids))
            )
            loaded_skus = result.scalars().all()

            # Cache the loaded SKUs for future requests
            for sku in loaded_skus:
                sku_objects[sku.id] = sku
                cached_data = serialize_sku_for_cache(sku)
                await cache.set_sku(sku.id, cached_data)
                cached_skus[sku.id] = cached_data

        # Step 4: For cache hits, load SKU objects for inventory reservation
        # (We still need the actual objects to call reserve_quantity)
        cache_hit_ids = [sku_id for sku_id, data in cached_skus.items() if data is not None and sku_id not in sku_objects]
        if cache_hit_ids:
            result = await db.execute(
                select(SKU).options(
                    selectinload(SKU.inventory),
                    selectinload(SKU.spu)
                ).filter(SKU.id.in_(cache_hit_ids))
            )
            for sku in result.scalars().all():
                sku_objects[sku.id] = sku

        # Step 5: Create order
        order = Order(
            order_number=order_number,
            customer_email=order_data.customer_email,
            customer_name=order_data.customer_name,
            subtotal=0,
            tax_amount=order_data.tax_amount or 0,
            shipping_amount=order_data.shipping_amount or 0,
            total_amount=0,
            currency=order_data.currency,
            notes=order_data.notes,
            flash_sale_id=order_data.flash_sale_id
        )
        db.add(order)
        await db.flush()  # Get order ID

        # Step 6: Process line items
        subtotal = Decimal(0)
        line_items_to_add = []

        for item_data in order_data.line_items:
            sku_id = str(item_data.sku_id)

            # Get SKU object
            sku = sku_objects.get(sku_id)
            if not sku:
                logger.warning(f"SKU not found: {sku_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"SKU {sku_id} not found"
                )

            # Use cached data for price (reduces object access)
            cached_sku_data = cached_skus[sku_id]

            # Check and reserve inventory
            if sku.track_inventory and sku.inventory:
                if not sku.inventory.can_fulfill_quantity(item_data.quantity):
                    logger.warning(
                        "Insufficient inventory for SKU",
                        extra={
                            "sku_code": sku.sku_code,
                            "requested": item_data.quantity,
                            "available": sku.inventory.available_quantity
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient inventory for SKU {sku.sku_code}"
                    )

                sku.inventory.reserve_quantity(item_data.quantity)
                # Invalidate inventory cache after modification
                await cache.invalidate_inventory(sku_id)

            # Create line item
            unit_price = item_data.unit_price or Decimal(str(cached_sku_data["price"]))
            total_price = unit_price * item_data.quantity

            line_item = OrderLineItem(
                order_id=order.id,
                sku_id=sku.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                total_price=total_price,
                product_name=cached_sku_data.get("spu_name") or sku.name or "Product",
                sku_code=sku.sku_code
            )
            line_items_to_add.append(line_item)
            subtotal += total_price

        # Step 7: Finalize order
        db.add_all(line_items_to_add)
        order.subtotal = subtotal
        order.total_amount = subtotal + order.tax_amount + order.shipping_amount

        await db.commit()

        # Reload with relationships for response
        result = await db.execute(
            select(Order).options(selectinload(Order.line_items)).filter(Order.id == order.id)
        )
        order = result.scalar_one()

        logger.info(
            "Order created successfully (Variant X)",
            extra={
                "order_id": str(order.id),
                "order_number": order.order_number,
                "total_amount": float(order.total_amount),
                "cache_hit_rate": f"{(cache_hits / len(sku_ids) * 100):.1f}%" if sku_ids else "0%"
            },
        )

        return ResponseDTO(status=201, message="Order created successfully", data=order)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(
            "Error creating order (Variant X)",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "order_data": order_data.model_dump(),
            },
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order due to an unexpected error.",
        )
