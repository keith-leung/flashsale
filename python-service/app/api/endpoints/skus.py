"""SKU (Stock Keeping Unit) endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.sku import SKU
from app.models.spu import SPU
from app.models.inventory import Inventory
from app.schemas.sku import SKUCreate, SKUUpdate, SKUResponse

router = APIRouter()


@router.get("/", response_model=List[SKUResponse])
async def list_skus(
    skip: int = 0,
    limit: int = 100,
    spu_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """List all SKUs."""
    query = select(SKU).options(selectinload(SKU.inventory))
    
    if spu_id:
        query = query.filter(SKU.spu_id == spu_id)
    
    query = query.offset(skip).limit(limit).order_by(SKU.created_at.desc())
    result = await db.execute(query)
    skus = result.scalars().all()
    
    # Add available quantity to response
    response_data = []
    for sku in skus:
        sku_dict = SKUResponse.from_orm(sku).dict()
        if sku.inventory:
            sku_dict['available_quantity'] = sku.inventory.available_quantity
        response_data.append(sku_dict)
    
    return response_data


@router.get("/{sku_id}", response_model=SKUResponse)
async def get_sku(sku_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific SKU by ID."""
    result = await db.execute(
        select(SKU).options(selectinload(SKU.inventory)).filter(SKU.id == sku_id)
    )
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )
    
    sku_dict = SKUResponse.from_orm(sku).dict()
    if sku.inventory:
        sku_dict['available_quantity'] = sku.inventory.available_quantity
    
    return sku_dict


@router.post("/", response_model=SKUResponse, status_code=status.HTTP_201_CREATED)
async def create_sku(sku_data: SKUCreate, db: AsyncSession = Depends(get_db)):
    """Create a new SKU."""
    # Check if SPU exists
    result = await db.execute(select(SPU).filter(SPU.id == sku_data.spu_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SPU not found"
        )
    
    # Check if SKU code already exists
    result = await db.execute(select(SKU).filter(SKU.sku_code == sku_data.sku_code))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU with this code already exists"
        )
    
    # Create SKU
    sku_dict = sku_data.dict()
    initial_quantity = sku_dict.pop('initial_quantity', 0)
    
    sku = SKU(**sku_dict)
    db.add(sku)
    await db.flush()  # Flush to get the ID
    
    # Create inventory record
    inventory = Inventory(sku_id=sku.id, quantity=initial_quantity)
    db.add(inventory)
    
    await db.commit()
    await db.refresh(sku)
    await db.refresh(inventory)
    
    sku_response = SKUResponse.from_orm(sku).dict()
    sku_response['available_quantity'] = inventory.available_quantity
    
    return sku_response


@router.put("/{sku_id}", response_model=SKUResponse)
async def update_sku(
    sku_id: UUID,
    sku_data: SKUUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing SKU."""
    result = await db.execute(
        select(SKU).options(selectinload(SKU.inventory)).filter(SKU.id == sku_id)
    )
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )
    
    # Check SKU code uniqueness if being updated
    if sku_data.sku_code and sku_data.sku_code != sku.sku_code:
        result = await db.execute(select(SKU).filter(SKU.sku_code == sku_data.sku_code))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU with this code already exists"
            )
    
    # Update fields
    update_data = sku_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sku, field, value)
    
    await db.commit()
    await db.refresh(sku)
    
    sku_dict = SKUResponse.from_orm(sku).dict()
    if sku.inventory:
        sku_dict['available_quantity'] = sku.inventory.available_quantity
    
    return sku_dict


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(sku_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a SKU."""
    result = await db.execute(select(SKU).filter(SKU.id == sku_id))
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )
    
    await db.delete(sku)
    await db.commit()
