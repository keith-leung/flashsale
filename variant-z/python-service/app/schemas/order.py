"""Order schemas for Variant Z."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class OrderLineItemRequest(BaseModel):
    """Order line item request schema."""
    sku_id: str = Field(..., description="SKU ID")
    quantity: int = Field(default=1, ge=1, le=10, description="Quantity (1-10)")


class OrderRequest(BaseModel):
    """Order creation request schema."""
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer name")
    customer_email: EmailStr = Field(..., description="Customer email")
    line_items: List[OrderLineItemRequest] = Field(..., min_length=1, max_length=1, description="Line items (single SKU only)")
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$", description="Currency code")
    
    @field_validator('line_items')
    @classmethod
    def validate_single_item(cls, v):
        """Ensure only one line item is provided."""
        if len(v) > 1:
            raise ValueError("Only single SKU orders are supported")
        return v


class OrderResponse(BaseModel):
    """Order response schema."""
    order_id: str = Field(..., description="Order ID")
    status: str = Field(..., description="Order status")
    total_amount: float = Field(..., description="Total amount")
    customer_email: EmailStr = Field(..., description="Customer email")
    
    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[dict] = Field(None, description="Additional error details")


class FlashSaleSoldOutResponse(BaseModel):
    """Flash sale sold out response."""
    error: str = Field(default="Flash sale sold out", description="Error type")
    campaign_id: str = Field(..., description="Campaign ID")
    sold_out_at: str = Field(..., description="Sold out timestamp (ISO 8601)")


class InsufficientStockResponse(BaseModel):
    """Insufficient stock response."""
    error: str = Field(default="Insufficient stock", description="Error type")
    sku_id: str = Field(..., description="SKU ID")
    available: int = Field(..., description="Available quantity")