"""Order schemas - Variant Zeta (Redis-First)."""

from pydantic import BaseModel, Field
from typing import List, Optional


class LineItemRequest(BaseModel):
    """Line item in an order."""
    sku_id: str = Field(..., description="SKU ID")
    quantity: int = Field(..., ge=1, le=10, description="Quantity (1-10)")


class OrderRequest(BaseModel):
    """Order creation request."""
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: str = Field(..., max_length=255, description="Customer email")
    line_items: List[LineItemRequest] = Field(..., min_length=1, max_length=5, description="Line items (1-5)")


class InsufficientStockResponse(BaseModel):
    """Insufficient stock error response."""
    sku_id: str
    available: int


class OrderCreatedResponse(BaseModel):
    """Order created response."""
    order_id: str
    status: str
    total_amount: float
    customer_email: str
