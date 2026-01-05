"""Order and transaction models."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Numeric, Enum as SQLEnum, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrderStatus(str, Enum):
    """Order status enumeration."""
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    pending = "pending"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"


class Order(Base):
    """Order model for both regular and flash sale orders."""
    
    __tablename__ = "orders"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Customer information
    customer_email = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    
    # Order totals
    subtotal = Column(Numeric(precision=10, scale=2), nullable=False)
    tax_amount = Column(Numeric(precision=10, scale=2), default=0, nullable=False)
    shipping_amount = Column(Numeric(precision=10, scale=2), default=0, nullable=False)
    total_amount = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Status and metadata
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.pending, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Flash sale campaign reference (optional) - SACRED schema compliant
    flash_sale_campaign_id = Column(CHAR(36), ForeignKey("flash_sale_campaigns.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    flash_sale_campaign = relationship("FlashSaleCampaign", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")
    
    def __str__(self):
        return f"Order {self.order_number}"


class OrderLineItem(Base):
    """Individual items within an order."""
    
    __tablename__ = "order_line_items"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(CHAR(36), ForeignKey("orders.id"), nullable=False, index=True)
    sku_id = Column(CHAR(36), ForeignKey("skus.id"), nullable=False, index=True)
    
    # Item details
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(precision=10, scale=2), nullable=False)
    total_price = Column(Numeric(precision=10, scale=2), nullable=False)
    
    # Product snapshot (in case SKU details change)
    product_name = Column(String(255), nullable=False)
    sku_code = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="line_items")
    sku = relationship("SKU")
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


class Payment(Base):
    """Payment transactions for orders."""
    
    __tablename__ = "payments"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(CHAR(36), ForeignKey("orders.id"), nullable=False, index=True)
    
    # Payment details
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    payment_method = Column(String(50), nullable=False)  # credit_card, paypal, etc.
    
    # Payment gateway information
    gateway_transaction_id = Column(String(255), nullable=True, index=True)
    gateway_response = Column(Text, nullable=True)  # JSON response from gateway
    
    # Status and metadata
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.pending, nullable=False, index=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="payments")
    
    def __str__(self):
        return f"Payment {self.amount} {self.currency} ({self.status})"
