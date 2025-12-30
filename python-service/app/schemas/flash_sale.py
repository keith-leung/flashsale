"""Flash Sale Event and Campaign schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.flash_sale import FlashSaleStatus, FlashSaleCampaignStatus


# ============================================================
# Flash Sale Campaign (SPU-Level) Schemas - Variant X
# ============================================================

class FlashSaleBase(BaseModel):
    """Base Flash Sale Campaign schema."""
    campaign_name: str = Field(..., min_length=1, max_length=255)
    spu_id: UUID
    total_sale_limit: int = Field(..., gt=0, description="Total units across ALL SKUs")
    start_time: datetime
    end_time: datetime
    flash_sale_price: Optional[Decimal] = Field(None, ge=0)
    max_per_order: int = Field(10, gt=0)

    @model_validator(mode='after')
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class FlashSaleCreate(FlashSaleBase):
    """Schema for creating a Flash Sale Campaign."""
    pass


class FlashSaleResponse(FlashSaleBase):
    """Schema for Flash Sale Campaign response."""
    id: UUID
    sold_count: int
    remaining_quantity: int
    percentage_sold: float
    status: FlashSaleCampaignStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlashSaleStatusResponse(BaseModel):
    """Schema for Flash Sale Status API response."""
    flash_sale_id: UUID
    campaign_name: str
    status: FlashSaleCampaignStatus
    start_time: datetime
    end_time: datetime
    total_limit: int
    remaining: int
    sold: int
    percentage_sold: float

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Flash Sale Event (SKU-Level) Schemas - Legacy
# ============================================================


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

    @model_validator(mode='after')
    def end_time_must_be_after_start_time(self):
        if self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


class FlashSaleEventCreate(FlashSaleEventBase):
    """Schema for creating a Flash Sale Event."""
    pass


class FlashSaleEventUpdate(BaseModel):
    """Schema for updating a Flash Sale Event."""
    name: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = None
    total_sale_limit: Optional[int] = Field(None, gt=0)
    max_quantity_per_customer: Optional[int] = Field(None, gt=0)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def end_time_must_be_after_start_time(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValueError('end_time must be after start_time')
        return self


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
    
    model_config = ConfigDict(from_attributes=True)


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
