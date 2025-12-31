"""Inventory management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryUpdate, InventoryResponse
from app.schemas.response import ResponseDTO

router = APIRouter()


@router.get("/{sku_id}", response_model=ResponseDTO[InventoryResponse])
async def get_inventory(sku_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get inventory for a specific SKU."""
    result = await db.execute(
        select(Inventory).filter(Inventory.sku_id == str(sku_id))
    )
    inventory = result.scalar_one_or_none()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this SKU"
        )
    
    return ResponseDTO(data=inventory)


@router.put("/{sku_id}", response_model=ResponseDTO[InventoryResponse])
async def update_inventory(
    sku_id: UUID,
    inventory_data: InventoryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update inventory for a specific SKU."""
    result = await db.execute(
        select(Inventory).filter(Inventory.sku_id == str(sku_id))
    )
    inventory = result.scalar_one_or_none()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this SKU"
        )
    
    # Update fields
    update_data = inventory_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)
    
    await db.commit()
    await db.refresh(inventory)
    
    return ResponseDTO(data=inventory)


@router.post("/{sku_id}/adjust", response_model=ResponseDTO[InventoryResponse])
async def adjust_inventory(
    sku_id: UUID,
    adjustment: int,
    reason: str = "Manual adjustment",
    db: AsyncSession = Depends(get_db)
):
    """Adjust inventory quantity (positive for increase, negative for decrease)."""
    result = await db.execute(
        select(Inventory).filter(Inventory.sku_id == str(sku_id))
    )
    inventory = result.scalar_one_or_none()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this SKU"
        )
    
    new_quantity = inventory.quantity + adjustment
    
    # Check if adjustment would result in negative stock when not allowed
    if new_quantity < 0 and not inventory.allow_negative_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment would result in negative stock. Current: {inventory.quantity}, Adjustment: {adjustment}"
        )
    
    inventory.quantity = new_quantity
    
    await db.commit()
    await db.refresh(inventory)
    
    return ResponseDTO(data=inventory)


@router.post("/{sku_id}/reserve", response_model=ResponseDTO[InventoryResponse])
async def reserve_inventory(
    sku_id: UUID,
    quantity: int,
    db: AsyncSession = Depends(get_db)
):
    """Reserve inventory quantity for an order."""
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    
    result = await db.execute(
        select(Inventory).filter(Inventory.sku_id == str(sku_id))
    )
    inventory = result.scalar_one_or_none()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this SKU"
        )
    
    if not inventory.reserve_quantity(quantity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reserve {quantity} items. Available: {inventory.available_quantity}"
        )
    
    await db.commit()
    await db.refresh(inventory)
    
    return ResponseDTO(data=inventory)


@router.post("/{sku_id}/release", response_model=ResponseDTO[InventoryResponse])
async def release_inventory(
    sku_id: UUID,
    quantity: int,
    db: AsyncSession = Depends(get_db)
):
    """Release reserved inventory quantity."""
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    
    result = await db.execute(
        select(Inventory).filter(Inventory.sku_id == str(sku_id))
    )
    inventory = result.scalar_one_or_none()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found for this SKU"
        )
    
    inventory.release_quantity(quantity)
    
    await db.commit()
    await db.refresh(inventory)
    
    return ResponseDTO(data=inventory)
