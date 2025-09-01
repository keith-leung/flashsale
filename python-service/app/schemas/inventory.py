"""Inventory schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InventoryUpdate(BaseModel):
    """Schema for updating inventory."""
    quantity: Optional[int] = Field(None, ge=0)
    allow_negative_stock: Optional[bool] = None


class InventoryResponse(BaseModel):
    """Schema for inventory response."""
    id: UUID
    sku_id: UUID
    quantity: int
    reserved_quantity: int
    available_quantity: int
    allow_negative_stock: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
