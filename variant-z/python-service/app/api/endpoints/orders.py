"""Orders API endpoint - Variant Z (Token Pre-Allocation with Synchronous Persistence)."""

import logging
import random
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.token_manager import token_manager
from app.core.redis import redis_client
from app.models.flash_sale import FlashSaleCampaign
from app.models.sku import SKU
from app.models.order import Order
from app.models.inventory import Inventory
from app.models.order_line_item import OrderLineItem
from app.models.payment import Payment
from app.schemas.order import (
    OrderRequest,
    OrderResponse,
    FlashSaleSoldOutResponse,
    InsufficientStockResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: Request,
    order_data: OrderRequest,
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """
    Create order with token pre-allocation (Variant Z).
    
    Handles both regular orders and flash sale orders:
    - Flash sale: Use Redis token acquisition
    - Regular: Use database transactions (Variant Y path)
    """
    request_start = time.time()
    
    # Get line item (Pydantic validates this)
    line_item = order_data.line_items[0]
    sku_id = line_item.sku_id
    quantity = line_item.quantity
    
    # Get SKU with inventory
    sku_result = await db.execute(
        select(SKU, Inventory)
        .join(Inventory, SKU.id == Inventory.sku_id)
        .where(SKU.id == sku_id)
        .where(SKU.is_active == True)
    )
    sku_inventory = sku_result.first()
    
    if not sku_inventory:
        raise HTTPException(status_code=404, detail="SKU not found")
    
    sku, inventory = sku_inventory
    
    # Check if SKU belongs to an active flash sale campaign
    campaign = await _get_active_campaign_for_sku(db, sku.spu_id)
    
    if campaign:
        # Variant Z path: Use token pre-allocation
        logger.info(f"SKU {sku_id} belongs to campaign {campaign.id}")
        
        # Check if campaign is sold out
        if await token_manager.is_campaign_sold_out(campaign.id):
            raise HTTPException(
                status_code=400,
                detail=FlashSaleSoldOutResponse(
                    campaign_id=campaign.id,
                    sold_out_at=datetime.utcnow().isoformat()
                ).model_dump()
            )
        
        # Acquire token atomically via Redis
        token_result = await token_manager.acquire_token(
            campaign_id=campaign.id,
            sku_id=sku_id,
            quantity=quantity
        )
        
        if 'err' in token_result:
            # Handle token acquisition errors
            error_code = token_result['err']
            logger.warning(f"Token acquisition failed: {error_code}")
            
            if error_code == "TOKEN_NOT_AVAILABLE":
                raise HTTPException(
                    status_code=400,
                    detail=FlashSaleSoldOutResponse(
                        campaign_id=campaign.id,
                        sold_out_at=datetime.utcnow().isoformat()
                    ).model_dump()
                )
            elif error_code == "INSUFFICIENT_STOCK":
                raise HTTPException(
                    status_code=400,
                    detail=InsufficientStockResponse(
                        sku_id=sku_id,
                        available=token_result.get('remaining_stock', 0)
                    ).model_dump()
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Token acquisition error: {error_code}"
                )
        
        # Token acquired successfully - proceed with order creation
        logger.info(f"Token acquired for campaign {campaign.id}, SKU {sku_id}")
        campaign_id_ref = campaign.id
    else:
        # Variant Y path: Use database transactions (no flash sale)
        logger.info(f"SKU {sku_id} not in active campaign - using Variant Y path")
        campaign_id_ref = None
        
        # Validate inventory
        if inventory.quantity < quantity:
            raise HTTPException(
                status_code=400,
                detail=InsufficientStockResponse(
                    sku_id=sku_id,
                    available=inventory.quantity
                ).model_dump()
            )
    
    # Generate order ID and number
    order_id = str(uuid.uuid4())
    timestamp = int(time.time_ns() // 1_000)  # Microsecond precision
    random_suffix = random.randint(1000, 9999)  # 4-digit random suffix
    order_number = f"ORD-{timestamp}-{random_suffix}"
    
    # Synchronously persist order to database (Variant Z requirement)
    await _persist_order_synchronously(
        db=db,
        order_id=order_id,
        order_number=order_number,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        sku_id=sku_id,
        quantity=quantity,
        unit_price=sku.price,
        campaign_id=campaign_id_ref,
        sku=sku
    )
    
    duration = time.time() - request_start
    logger.info(
        f"Order created (sync): {order_id} ({duration:.3f}s)",
        extra={
            "order_id": order_id,
            "duration_sec": round(duration, 3),
            "campaign_id": campaign_id_ref,
            "sku_id": sku_id,
            "quantity": quantity,
            "persistence": "synchronous"
        }
    )
    
    return OrderResponse(
        order_id=order_id,
        status="pending",
        total_amount=float(quantity * sku.price),
        customer_email=order_data.customer_email
    )


async def _get_active_campaign_for_sku(
    db: AsyncSession, 
    spu_id: str
) -> Optional[FlashSaleCampaign]:
    """Get active flash sale campaign for SPU."""
    now = datetime.utcnow()
    
    result = await db.execute(
        select(FlashSaleCampaign)
        .where(FlashSaleCampaign.spu_id == spu_id)
        .where(FlashSaleCampaign.is_active == True)
        .where(FlashSaleCampaign.status == "active")
        .where(FlashSaleCampaign.start_time <= now)
        .where(FlashSaleCampaign.end_time >= now)
    )
    
    return result.scalar_one_or_none()


async def _persist_order_synchronously(
    db: AsyncSession,
    order_id: str,
    order_number: str,
    customer_name: str,
    customer_email: str,
    sku_id: str,
    quantity: int,
    unit_price: float,
    campaign_id: Optional[str],
    sku: SKU
):
    """
    Synchronously persist order to database (Variant Z requirement).
    
    This is the hot path - writes to database synchronously before returning 201.
    All operations happen in a single transaction to ensure ACID guarantees.
    """
    # Calculate totals
    subtotal = quantity * unit_price
    total_amount = subtotal  # No tax/shipping for flash sales
    
    # Create order
    order = Order(
        id=order_id,
        order_number=order_number,
        customer_email=customer_email,
        customer_name=customer_name,
        subtotal=subtotal,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=total_amount,
        currency="USD",
        status="pending",
        flash_sale_campaign_id=campaign_id
    )
    
    db.add(order)
    
    # Create order line item
    line_item = OrderLineItem(
        id=str(uuid.uuid4()),
        order_id=order_id,
        sku_id=sku_id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=subtotal,
        product_name=sku.name,
        sku_code=sku.sku_code
    )
    
    db.add(line_item)
    
    # Create payment record
    payment = Payment(
        id=str(uuid.uuid4()),
        order_id=order_id,
        amount=total_amount,
        currency="USD",
        payment_method="flash_sale",
        gateway_transaction_id=f"TXN-{int(time.time_ns() // 1_000_000)}",
        gateway_response="",
        status="authorized"
    )
    
    db.add(payment)
    
    # Update inventory
    inventory_result = await db.execute(
        select(Inventory).where(Inventory.sku_id == sku_id)
    )
    inventory = inventory_result.scalar_one_or_none()
    
    if inventory:
        inventory.quantity -= quantity
        inventory.reserved_quantity += quantity
    
    # Update campaign sold quantity (if flash sale)
    if campaign_id:
        campaign_result = await db.execute(
            select(FlashSaleCampaign).where(FlashSaleCampaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        
        if campaign:
            campaign.sold_quantity += quantity
            campaign.updated_at = datetime.utcnow()
    
    # Commit transaction (synchronous)
    await db.commit()
    
    logger.debug(f"Order {order_id} persisted synchronously to database")


@router.get("/test-data")
async def test_order_data():
    """Test endpoint to verify order creation."""
    return {
        "message": "Variant Z - Token Pre-Allocation",
        "endpoints": {
            "POST /api/v1/orders": "Create order (with or without flash sale)",
            "GET /api/v1/orders/test-data": "This endpoint"
        },
        "architecture": {
            "token_pre_allocation": True,
            "redis_enabled": True,
            "synchronous_database_persistence": True,
            "wal_pattern": False,
            "description": "Pre-allocate tokens in Redis, acquire atomically via Lua, persist synchronously to database"
        }
    }