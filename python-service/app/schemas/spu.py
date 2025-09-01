"""SPU (Standard Product Unit) schemas."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class SPUBase(BaseModel):
    """Base SPU schema."""
    name: str = Field(..., min_length=1, max_length=250)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class SPUCreate(SPUBase):
    """Schema for creating an SPU."""
    pass


class SPUUpdate(BaseModel):
    """Schema for updating an SPU."""
    name: Optional[str] = Field(None, min_length=1, max_length=250)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SPUResponse(SPUBase):
    """Schema for SPU response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
