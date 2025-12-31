"""SKU (Stock Keeping Unit) schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SKUBase(BaseModel):
    """Base SKU schema."""
    sku_code: str = Field(..., min_length=1, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    spu_id: UUID
    price: Decimal = Field(..., gt=0, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    weight: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    track_inventory: bool = True
    is_active: bool = True


class SKUCreate(SKUBase):
    """Schema for creating a SKU."""
    initial_quantity: int = Field(0, ge=0, description="Initial inventory quantity")


class SKUUpdate(BaseModel):
    """Schema for updating a SKU."""
    sku_code: Optional[str] = Field(None, min_length=1, max_length=255)
    name: Optional[str] = Field(None, max_length=255)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    cost_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    weight: Optional[Decimal] = Field(None, ge=0, decimal_places=3)
    track_inventory: Optional[bool] = None
    is_active: Optional[bool] = None


class SKUResponse(SKUBase):
    """Schema for SKU response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    available_quantity: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
