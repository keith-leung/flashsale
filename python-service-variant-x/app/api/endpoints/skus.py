
import logging
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
from app.schemas.response import ResponseDTO

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=ResponseDTO[List[SKUResponse]])
async def list_skus(
    skip: int = 0,
    limit: int = 100,
    spu_id: UUID = None,
    db: AsyncSession = Depends(get_db)
):
    """List all SKUs."""
    query = select(SKU).options(selectinload(SKU.inventory))
    
    if spu_id:
        query = query.filter(SKU.spu_id == str(spu_id))
    
    query = query.offset(skip).limit(limit).order_by(SKU.created_at.desc())
    result = await db.execute(query)
    skus = result.scalars().all()
    
    # Add available quantity to response
    response_data = []
    for sku in skus:
        sku_response = SKUResponse.model_validate(sku)
        if sku.inventory:
            sku_response.available_quantity = sku.inventory.available_quantity
        response_data.append(sku_response)
    
    return ResponseDTO(data=response_data)


@router.get("/{sku_id}", response_model=ResponseDTO[SKUResponse])
async def get_sku(sku_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific SKU by ID."""
    result = await db.execute(
        select(SKU).options(selectinload(SKU.inventory)).filter(SKU.id == str(sku_id))
    )
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )

    sku_response = SKUResponse.model_validate(sku)
    if sku.inventory:
        sku_response.available_quantity = sku.inventory.available_quantity

    return ResponseDTO(data=sku_response)


@router.post("", response_model=ResponseDTO[SKUResponse], status_code=status.HTTP_201_CREATED)
async def create_sku(sku_data: SKUCreate, db: AsyncSession = Depends(get_db)):
    """Create a new SKU."""
    logger.info(
        "Starting SKU creation",
        extra={"sku_code": sku_data.sku_code, "spu_id": str(sku_data.spu_id)},
    )
    
    try:
        # Check if SPU exists
        result = await db.execute(select(SPU).filter(SPU.id == str(sku_data.spu_id)))
        spu = result.scalar_one_or_none()
        logger.info("SPU query result", extra={"spu": spu})
        if not spu:
            logger.warning(
                "SPU not found during SKU creation",
                extra={"spu_id": str(sku_data.spu_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SPU not found",
            )
        
        # Check if SKU code already exists
        result = await db.execute(select(SKU).filter(SKU.sku_code == sku_data.sku_code))
        if result.scalar_one_or_none():
            logger.warning(
                "SKU with code already exists",
                extra={"sku_code": sku_data.sku_code},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SKU with this code already exists",
            )
        
        # Create SKU and Inventory
        sku_dict = sku_data.model_dump()
        initial_quantity = sku_dict.pop('initial_quantity', 0)
        
        sku = SKU(**sku_dict)
        db.add(sku)
        await db.flush()  # Flush to get the SKU ID
        
        inventory = Inventory(sku_id=sku.id, quantity=initial_quantity)
        db.add(inventory)
        
        await db.commit()
        await db.refresh(sku)
        await db.refresh(inventory)

        sku_response = SKUResponse.model_validate(sku)
        sku_response.available_quantity = inventory.available_quantity
        
        logger.info(
            "SKU created successfully",
            extra={
                "sku_id": str(sku.id),
                "sku_code": sku.sku_code,
                "inventory_id": str(inventory.id),
                "initial_quantity": initial_quantity,
            },
        )
        
        return ResponseDTO(status=201, message="SKU created successfully", data=sku_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating SKU",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "sku_data": sku_data.model_dump(),
            },
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SKU due to an unexpected error.",
        )


@router.put("/{sku_id}", response_model=ResponseDTO[SKUResponse])
async def update_sku(
    sku_id: UUID,
    sku_data: SKUUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing SKU."""
    result = await db.execute(
        select(SKU).options(selectinload(SKU.inventory)).filter(SKU.id == str(sku_id))
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
    update_data = sku_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sku, field, value)
    
    await db.commit()
    await db.refresh(sku)

    sku_response = SKUResponse.model_validate(sku)
    if sku.inventory:
        sku_response.available_quantity = sku.inventory.available_quantity

    return ResponseDTO(data=sku_response)


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sku(sku_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a SKU."""
    result = await db.execute(select(SKU).filter(SKU.id == str(sku_id)))
    sku = result.scalar_one_or_none()
    
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found"
        )
    
    await db.delete(sku)
    await db.commit()
    return ResponseDTO(status=204, message="SKU deleted successfully")
