"""Order and payment schemas."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.order import OrderStatus, PaymentStatus


class OrderLineItemCreate(BaseModel):
    """Schema for creating an order line item."""
    sku_id: str
    quantity: int = Field(..., gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)


class OrderLineItemResponse(BaseModel):
    """Schema for order line item response."""
    id: str
    sku_id: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    product_name: str
    sku_code: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Schema for creating an order."""
    customer_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    customer_name: Optional[str] = None
    tax_amount: Optional[Decimal] = Field(0, ge=0, decimal_places=2)
    shipping_amount: Optional[Decimal] = Field(0, ge=0, decimal_places=2)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None
    flash_sale_id: Optional[str] = None
    line_items: List[OrderLineItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    """Schema for updating an order."""
    customer_name: Optional[str] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    """Schema for order response."""
    id: str
    order_number: str
    customer_email: str
    customer_name: Optional[str]
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    currency: str
    status: OrderStatus
    notes: Optional[str]
    flash_sale_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    line_items: List[OrderLineItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    """Schema for creating a payment."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("USD", min_length=3, max_length=3)
    payment_method: str = Field(..., min_length=1)
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    """Schema for payment response."""
    id: str
    order_id: str
    amount: Decimal
    currency: str
    payment_method: str
    gateway_transaction_id: Optional[str]
    status: PaymentStatus
    reference_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
