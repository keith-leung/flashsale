"""Flash Sale Campaign schemas - SPU-level campaigns."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, model_validator

from app.models.flash_sale import FlashSaleStatus


class FlashSaleCampaignBase(BaseModel):
    """Base Flash Sale Campaign schema."""
    name: str = Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    spu_id: UUID  # Links to product family (SPU), NOT variant (SKU)!
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


class FlashSaleCampaignCreate(FlashSaleCampaignBase):
    """Schema for creating a Flash Sale Campaign."""
    pass


class FlashSaleCampaignUpdate(BaseModel):
    """Schema for updating a Flash Sale Campaign."""
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


class FlashSaleCampaignResponse(FlashSaleCampaignBase):
    """Schema for Flash Sale Campaign response."""
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
    """Schema for purchasing from a flash sale campaign.

    NOTE: This endpoint is DEPRECATED - use /api/v1/orders instead!
    Frontend should NEVER call this endpoint for purchases.
    """
    quantity: int = Field(..., gt=0)
    customer_id: Optional[str] = None  # Optional customer identification


class PurchaseResponse(BaseModel):
    """Schema for purchase response."""
    success: bool
    message: str
    flash_sale_campaign_id: UUID
    quantity_purchased: int
    remaining_quantity: int
