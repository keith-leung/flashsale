"""Flash Sale Event schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.models.flash_sale import FlashSaleStatus


class FlashSaleEventBase(BaseModel):
    """Base Flash Sale Event schema."""
    name: str = Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    sku_id: UUID
    total_sale_limit: int = Field(..., gt=0)
    max_quantity_per_customer: int = Field(1, gt=0)
    start_time: datetime
    end_time: datetime
    is_active: bool = True


class FlashSaleEventCreate(FlashSaleEventBase):
    """Schema for creating a Flash Sale Event."""
    
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class FlashSaleEventUpdate(BaseModel):
    """Schema for updating a Flash Sale Event."""
    name: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = None
    total_sale_limit: Optional[int] = Field(None, gt=0)
    max_quantity_per_customer: Optional[int] = Field(None, gt=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: Optional[bool] = None
    
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        if v is not None and 'start_time' in values and values['start_time'] is not None:
            if v <= values['start_time']:
                raise ValueError('end_time must be after start_time')
        return v


class FlashSaleEventResponse(FlashSaleEventBase):
    """Schema for Flash Sale Event response."""
    id: UUID
    sold_quantity: int
    remaining_quantity: int
    status: FlashSaleStatus
    is_time_active: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PurchaseRequest(BaseModel):
    """Schema for purchasing from a flash sale."""
    quantity: int = Field(..., gt=0)
    customer_id: Optional[str] = None  # Optional customer identification


class PurchaseResponse(BaseModel):
    """Schema for purchase response."""
    success: bool
    message: str
    flash_sale_id: UUID
    quantity_purchased: int
    remaining_quantity: int
