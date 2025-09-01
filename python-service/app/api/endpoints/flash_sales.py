"""Flash Sale Event endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.flash_sale import FlashSaleEvent, FlashSaleStatus
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.schemas.flash_sale import (
    FlashSaleEventCreate,
    FlashSaleEventUpdate,
    FlashSaleEventResponse,
    PurchaseRequest,
    PurchaseResponse
)

router = APIRouter()


@router.get("/", response_model=List[FlashSaleEventResponse])
async def list_flash_sales(
    skip: int = 0,
    limit: int = 100,
    status_filter: FlashSaleStatus = None,
    db: AsyncSession = Depends(get_db)
):
    """List all flash sale events."""
    query = select(FlashSaleEvent)
    
    if status_filter:
        query = query.filter(FlashSaleEvent.status == status_filter)
    
    query = query.offset(skip).limit(limit).order_by(FlashSaleEvent.created_at.desc())
    result = await db.execute(query)
    flash_sales = result.scalars().all()
    
    # Update status for each flash sale before returning
    for flash_sale in flash_sales:
        flash_sale.update_status()
    
    await db.commit()
    
    return flash_sales


@router.get("/{flash_sale_id}", response_model=FlashSaleEventResponse)
async def get_flash_sale(flash_sale_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific flash sale event by ID."""
    result = await db.execute(
        select(FlashSaleEvent).filter(FlashSaleEvent.id == flash_sale_id)
    )
    flash_sale = result.scalar_one_or_none()
    
    if not flash_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flash sale event not found"
        )
    
    # Update status before returning
    flash_sale.update_status()
    await db.commit()
    
    return flash_sale


@router.post("/", response_model=FlashSaleEventResponse, status_code=status.HTTP_201_CREATED)
async def create_flash_sale(
    flash_sale_data: FlashSaleEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new flash sale event."""
    # Check if SKU exists
    result = await db.execute(select(SKU).filter(SKU.id == flash_sale_data.sku_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU not found"
        )
    
    flash_sale = FlashSaleEvent(**flash_sale_data.dict())
    flash_sale.update_status()  # Set initial status
    
    db.add(flash_sale)
    await db.commit()
    await db.refresh(flash_sale)
    
    return flash_sale


@router.put("/{flash_sale_id}", response_model=FlashSaleEventResponse)
async def update_flash_sale(
    flash_sale_id: UUID,
    flash_sale_data: FlashSaleEventUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing flash sale event."""
    result = await db.execute(
        select(FlashSaleEvent).filter(FlashSaleEvent.id == flash_sale_id)
    )
    flash_sale = result.scalar_one_or_none()
    
    if not flash_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flash sale event not found"
        )
    
    # Update fields
    update_data = flash_sale_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flash_sale, field, value)
    
    flash_sale.update_status()  # Recalculate status
    
    await db.commit()
    await db.refresh(flash_sale)
    
    return flash_sale


@router.post("/{flash_sale_id}/purchase", response_model=PurchaseResponse)
async def purchase_flash_sale(
    flash_sale_id: UUID,
    purchase_data: PurchaseRequest,
    db: AsyncSession = Depends(get_db)
):
    """Purchase items from a flash sale event."""
    # Get flash sale with related SKU and inventory
    result = await db.execute(
        select(FlashSaleEvent)
        .options(
            selectinload(FlashSaleEvent.sku).selectinload(SKU.inventory)
        )
        .filter(FlashSaleEvent.id == flash_sale_id)
    )
    flash_sale = result.scalar_one_or_none()
    
    if not flash_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flash sale event not found"
        )
    
    # Update flash sale status
    flash_sale.update_status()
    
    # Check if purchase is valid
    if not flash_sale.can_purchase_quantity(purchase_data.quantity):
        reasons = []
        if not flash_sale.is_active:
            reasons.append("Flash sale is not active")
        if not flash_sale.is_time_active:
            reasons.append("Flash sale is not within time window")
        if flash_sale.remaining_quantity < purchase_data.quantity:
            reasons.append(f"Not enough items available (only {flash_sale.remaining_quantity} left)")
        if purchase_data.quantity > flash_sale.max_quantity_per_customer:
            reasons.append(f"Quantity exceeds maximum per customer ({flash_sale.max_quantity_per_customer})")
        
        return PurchaseResponse(
            success=False,
            message=f"Purchase failed: {'; '.join(reasons)}",
            flash_sale_id=flash_sale_id,
            quantity_purchased=0,
            remaining_quantity=flash_sale.remaining_quantity
        )
    
    # Check inventory availability
    inventory = flash_sale.sku.inventory
    if inventory and not inventory.can_fulfill_quantity(purchase_data.quantity):
        return PurchaseResponse(
            success=False,
            message=f"Insufficient inventory (only {inventory.available_quantity} available)",
            flash_sale_id=flash_sale_id,
            quantity_purchased=0,
            remaining_quantity=flash_sale.remaining_quantity
        )
    
    # Perform the purchase
    success = flash_sale.purchase_quantity(purchase_data.quantity)
    if not success:
        return PurchaseResponse(
            success=False,
            message="Purchase failed due to unexpected error",
            flash_sale_id=flash_sale_id,
            quantity_purchased=0,
            remaining_quantity=flash_sale.remaining_quantity
        )
    
    # Update inventory if tracking is enabled
    if inventory and flash_sale.sku.track_inventory:
        inventory.fulfill_quantity(purchase_data.quantity)
    
    await db.commit()
    
    return PurchaseResponse(
        success=True,
        message=f"Successfully purchased {purchase_data.quantity} items",
        flash_sale_id=flash_sale_id,
        quantity_purchased=purchase_data.quantity,
        remaining_quantity=flash_sale.remaining_quantity
    )


@router.delete("/{flash_sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flash_sale(flash_sale_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a flash sale event."""
    result = await db.execute(
        select(FlashSaleEvent).filter(FlashSaleEvent.id == flash_sale_id)
    )
    flash_sale = result.scalar_one_or_none()
    
    if not flash_sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flash sale event not found"
        )
    
    await db.delete(flash_sale)
    await db.commit()
