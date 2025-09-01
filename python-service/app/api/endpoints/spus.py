"""SPU (Standard Product Unit) endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.spu import SPU
from app.schemas.spu import SPUCreate, SPUUpdate, SPUResponse

router = APIRouter()


@router.get("/", response_model=List[SPUResponse])
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
    return spus


@router.get("/{spu_id}", response_model=SPUResponse)
async def get_spu(spu_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a specific SPU by ID."""
    result = await db.execute(select(SPU).filter(SPU.id == spu_id))
    spu = result.scalar_one_or_none()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU not found"
        )
    
    return spu


@router.post("/", response_model=SPUResponse, status_code=status.HTTP_201_CREATED)
async def create_spu(spu_data: SPUCreate, db: AsyncSession = Depends(get_db)):
    """Create a new SPU."""
    # Check if slug already exists
    result = await db.execute(select(SPU).filter(SPU.slug == spu_data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SPU with this slug already exists"
        )
    
    spu = SPU(**spu_data.dict())
    db.add(spu)
    await db.commit()
    await db.refresh(spu)
    
    return spu


@router.put("/{spu_id}", response_model=SPUResponse)
async def update_spu(
    spu_id: UUID,
    spu_data: SPUUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing SPU."""
    result = await db.execute(select(SPU).filter(SPU.id == spu_id))
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
    update_data = spu_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(spu, field, value)
    
    await db.commit()
    await db.refresh(spu)
    
    return spu


@router.delete("/{spu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spu(spu_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an SPU."""
    result = await db.execute(select(SPU).filter(SPU.id == spu_id))
    spu = result.scalar_one_or_none()
    
    if not spu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SPU not found"
        )
    
    await db.delete(spu)
    await db.commit()
