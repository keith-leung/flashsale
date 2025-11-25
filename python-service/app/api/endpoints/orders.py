
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.id_generator import generate_id
from app.models.order import Order, OrderLineItem, Payment, OrderStatus, PaymentStatus
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse,
    PaymentCreate, PaymentResponse,
    OrderLineItemResponse
)
from app.schemas.response import ResponseDTO

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=ResponseDTO[List[OrderResponse]])
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
    order_responses = [OrderResponse.model_validate(order) for order in orders]

    return ResponseDTO(data=order_responses)


@router.get("/{order_id}", response_model=ResponseDTO[OrderResponse])
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
    
    return ResponseDTO(data=order)


@router.post("", response_model=ResponseDTO[OrderResponse], status_code=status.HTTP_201_CREATED)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new order."""
    order_number = f"ORD-{generate_id()}"
    logger.info(
        "Starting order creation",
        extra={
            "order_number": order_number,
            "customer_email": order_data.customer_email,
        },
    )
    
    try:
        # Create a new order instance
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
        await db.flush()  # Flush to get the order ID

        subtotal = 0
        line_items_to_add = []

        # Process each line item
        for item_data in order_data.line_items:
            # Fetch SKU and inventory
            result = await db.execute(
                select(SKU).options(selectinload(SKU.inventory), selectinload(SKU.spu)).filter(SKU.id == str(item_data.sku_id))
            )
            sku = result.scalar_one_or_none()

            if not sku:
                logger.warning("SKU not found during order creation", extra={"sku_id": str(item_data.sku_id)})
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"SKU {item_data.sku_id} not found")

            # Check and reserve inventory
            if sku.track_inventory and sku.inventory:
                if not sku.inventory.can_fulfill_quantity(item_data.quantity):
                    logger.warning(
                        "Insufficient inventory for SKU",
                        extra={"sku_code": sku.sku_code, "requested": item_data.quantity, "available": sku.inventory.available_quantity},
                    )
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient inventory for SKU {sku.sku_code}")
                
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
                product_name=getattr(sku.spu, 'name', sku.name or "Product"),
                sku_code=sku.sku_code
            )
            line_items_to_add.append(line_item)
            subtotal += total_price

        # Add all line items to the session
        db.add_all(line_items_to_add)

        # Update order totals
        order.subtotal = subtotal
        order.total_amount = subtotal + order.tax_amount + order.shipping_amount

        await db.commit()
        # Eagerly load the line_items relationship for the response model
        result = await db.execute(
            select(Order).options(selectinload(Order.line_items)).filter(Order.id == order.id)
        )
        order = result.scalar_one()

        logger.info(
            "Order created successfully",
            extra={"order_id": str(order.id), "order_number": order.order_number, "total_amount": order.total_amount},
        )

        return ResponseDTO(status=201, message="Order created successfully", data=order)

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(
            "Error creating order",
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


@router.put("/{order_id}", response_model=ResponseDTO[OrderResponse])
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing order."""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.line_items))
        .filter(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update fields
    update_data = order_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    await db.commit()
    await db.refresh(order)
    
    return ResponseDTO(data=order)


@router.post("/{order_id}/payments", response_model=ResponseDTO[PaymentResponse])
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
        payment.status = PaymentStatus.captured
        payment.gateway_transaction_id = f"txn_{generate_id()}"
        
        # Update order status
        order.status = OrderStatus.confirmed
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    return ResponseDTO(data=payment)


@router.post("/{order_id}/fulfill", response_model=ResponseDTO[OrderResponse])
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
    
    if order.status != OrderStatus.confirmed:
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
    order.status = OrderStatus.shipped
    
    await db.commit()
    await db.refresh(order)
    
    return ResponseDTO(data=order)

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an order."""
    result = await db.execute(select(Order).filter(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    await db.delete(order)
    await db.commit()
    return ResponseDTO(status=204, message="Order deleted successfully")
