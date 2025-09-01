"""Order management endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.order import Order, OrderLineItem, Payment, OrderStatus, PaymentStatus
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse,
    PaymentCreate, PaymentResponse,
    OrderLineItemResponse
)

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: OrderStatus = None,
    customer_email: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all orders."""
    query = select(Order).options(
        selectinload(Order.line_items),
        selectinload(Order.payments)
    )
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    if customer_email:
        query = query.filter(Order.customer_email == customer_email)
    
    query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific order by ID."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.line_items),
            selectinload(Order.payments),
            selectinload(Order.flash_sale)
        )
        .filter(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new order."""
    
    # Generate order number
    import time
    order_number = f"ORD-{int(time.time())}-{order_data.customer_email[:3].upper()}"
    
    # Create order
    order = Order(
        order_number=order_number,
        customer_email=order_data.customer_email,
        customer_name=order_data.customer_name,
        subtotal=0,  # Will be calculated
        tax_amount=order_data.tax_amount or 0,
        shipping_amount=order_data.shipping_amount or 0,
        total_amount=0,  # Will be calculated
        currency=order_data.currency,
        notes=order_data.notes,
        flash_sale_id=order_data.flash_sale_id
    )
    
    db.add(order)
    await db.flush()  # Get the order ID
    
    # Add line items and calculate totals
    subtotal = 0
    for item_data in order_data.line_items:
        # Get SKU information
        result = await db.execute(
            select(SKU).options(selectinload(SKU.inventory)).filter(SKU.id == item_data.sku_id)
        )
        sku = result.scalar_one_or_none()
        
        if not sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU {item_data.sku_id} not found"
            )
        
        # Check inventory
        if sku.track_inventory and sku.inventory:
            if not sku.inventory.can_fulfill_quantity(item_data.quantity):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient inventory for SKU {sku.sku_code}"
                )
            
            # Reserve inventory
            sku.inventory.reserve_quantity(item_data.quantity)
        
        # Create line item
        unit_price = item_data.unit_price or sku.price
        total_price = unit_price * item_data.quantity
        
        line_item = OrderLineItem(
            order_id=order.id,
            sku_id=sku.id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=total_price,
            product_name=sku.spu.name if sku.spu else sku.name or "Product",
            sku_code=sku.sku_code
        )
        
        db.add(line_item)
        subtotal += total_price
    
    # Update order totals
    order.subtotal = subtotal
    order.total_amount = subtotal + order.tax_amount + order.shipping_amount
    
    await db.commit()
    await db.refresh(order)
    
    return order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing order."""
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update fields
    update_data = order_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    return order


@router.post("/{order_id}/payments", response_model=PaymentResponse)
async def create_payment(
    order_id: str,
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a payment for an order."""
    # Verify order exists
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Create payment
    payment = Payment(
        order_id=order_id,
        amount=payment_data.amount,
        currency=payment_data.currency,
        payment_method=payment_data.payment_method,
        reference_number=payment_data.reference_number,
        notes=payment_data.notes
    )
    
    # Simulate payment processing
    if payment_data.amount > 0:
        payment.status = PaymentStatus.CAPTURED
        payment.gateway_transaction_id = f"txn_{int(time.time())}"
        
        # Update order status
        order.status = OrderStatus.CONFIRMED
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    return payment


@router.post("/{order_id}/fulfill", response_model=OrderResponse)
async def fulfill_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Fulfill an order by updating inventory and status."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.line_items).selectinload(OrderLineItem.sku).selectinload(SKU.inventory))
        .filter(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be confirmed before fulfillment"
        )
    
    # Fulfill inventory for each line item
    for line_item in order.line_items:
        sku = line_item.sku
        if sku.track_inventory and sku.inventory:
            if not sku.inventory.fulfill_quantity(line_item.quantity):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot fulfill quantity for SKU {sku.sku_code}"
                )
    
    # Update order status
    order.status = OrderStatus.SHIPPED
    
    await db.commit()
    await db.refresh(order)
    
    return order
