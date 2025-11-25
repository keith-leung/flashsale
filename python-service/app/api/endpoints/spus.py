"""SPU (Standard Product Unit) endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.spu import SPU
from app.schemas.spu import SPUCreate, SPUUpdate, SPUResponse
from app.schemas.response import ResponseDTO

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=ResponseDTO[List[SPUResponse]])
async def list_spus(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all SPUs."""
    result = await db.execute(
        select(SPU).offset(skip).limit(limit).order_by(SPU.created_at.desc())
    )
    spus = result.scalars().all()
    spu_responses = [SPUResponse.model_validate(spu) for spu in spus]
    return ResponseDTO(data=spu_responses)


@router.get("/{spu_id}", response_model=ResponseDTO[SPUResponse])
async def get_spu(spu_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific SPU by ID."""
    result = await db.execute(select(SPU).filter(SPU.id == str(spu_id)))
    spu = result.scalar_one_or_none()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU not found"
        )
    
    return ResponseDTO(data=spu)


@router.post("", response_model=ResponseDTO[SPUResponse], status_code=status.HTTP_201_CREATED)
async def create_spu(spu_data: SPUCreate, db: AsyncSession = Depends(get_db)):
    """Create a new SPU."""
    logger.info(
        "Starting SPU creation",
        extra={"slug": spu_data.slug, "spu_data": spu_data.model_dump()},
    )
    
    try:
        # Check if slug already exists
        result = await db.execute(select(SPU).filter(SPU.slug == spu_data.slug))
        if result.scalar_one_or_none():
            logger.warning(
                "SPU with slug already exists",
                extra={"slug": spu_data.slug},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SPU with this slug already exists",
            )
        
        spu = SPU(**spu_data.model_dump())
        db.add(spu)
        await db.commit()
        await db.refresh(spu)
        
        logger.info(
            "SPU created successfully",
            extra={"spu_id": str(spu.id), "slug": spu.slug},
        )
        return ResponseDTO(status=201, message="SPU created successfully", data=spu)
    except HTTPException:
        # Re-raise HTTP exceptions to be handled by FastAPI's default error handling
        raise
    except Exception as e:
        logger.error(
            "Error creating SPU",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "spu_data": spu_data.model_dump(),
            },
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create SPU due to an unexpected error.",
        )


@router.put("/{spu_id}", response_model=ResponseDTO[SPUResponse])
async def update_spu(
    spu_id: UUID,
    spu_data: SPUUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing SPU."""
    result = await db.execute(select(SPU).filter(SPU.id == str(spu_id)))
    spu = result.scalar_one_or_none()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU not found"
        )
    
    # Check slug uniqueness if being updated
    if spu_data.slug and spu_data.slug != spu.slug:
        result = await db.execute(select(SPU).filter(SPU.slug == spu_data.slug))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SPU with this slug already exists"
            )
    
    # Update fields
    update_data = spu_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spu, field, value)
    
    await db.commit()
    await db.refresh(spu)
    
    return ResponseDTO(data=spu)


@router.delete("/{spu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spu(spu_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an SPU."""
    result = await db.execute(select(SPU).filter(SPU.id == str(spu_id)))
    spu = result.scalar_one_or_none()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU not found"
        )
    
    await db.delete(spu)
    await db.commit()
    return ResponseDTO(status=204, message="SPU deleted successfully")
