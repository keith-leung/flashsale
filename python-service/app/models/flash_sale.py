"""Flash Sale Campaign model - SPU-level campaigns."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer, Boolean, Enum as SQLEnum, Numeric
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class FlashSaleStatus(str, Enum):
    """Flash sale status enumeration."""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class FlashSaleCampaign(Base):
    """Flash Sale Campaign - SPU-level (product family) with time-based controls and sale limits.

    CRITICAL: Campaigns are SPU-level, NOT SKU-level!
    Example: Campaign for "iPhone 16" (SPU) with 100K total_sale_limit
             Customers order "iPhone 16 Black 512GB" or "iPhone 16 Silver 128GB" (SKUs)
             Campaign tracks total across ALL SKUs under the SPU
    """

    __tablename__ = "flash_sale_campaigns"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(250), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Foreign Keys - Links to SPU (product family), NOT SKU (variant)!
    spu_id = Column(CHAR(36), ForeignKey("spus.id"), nullable=False, index=True)
    
    # Sale constraints
    total_sale_limit = Column(Integer, nullable=False)  # Total units across ALL SKUs under this SPU
    sold_quantity = Column(Integer, default=0, nullable=False)  # Incremented when ANY SKU under this SPU is ordered
    max_quantity_per_customer = Column(Integer, default=1, nullable=False)  # Max per customer
    flash_price = Column(Numeric(10, 2), nullable=False)  # Special campaign price (cheaper than regular SKU price)

    # Time constraints
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)

    # Status and flags
    status = Column(String(20), default="scheduled", nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    spu = relationship("SPU")  # Links to product family
    orders = relationship("Order", back_populates="flash_sale_campaign")
    
    @property
    def remaining_quantity(self):
        """Calculate remaining quantity available for sale."""
        return max(0, self.total_sale_limit - self.sold_quantity)
    
    @property
    def is_time_active(self):
        """Check if the flash sale is currently within its time window."""
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time
    
    @property
    def is_available(self):
        """Check if the flash sale is currently available for purchase."""
        return (
            self.is_active
            and self.status == "active"
            and self.is_time_active
            and self.remaining_quantity > 0
        )
    
    def can_purchase_quantity(self, quantity: int) -> bool:
        """Check if the requested quantity can be purchased."""
        if not self.is_available:
            return False
        if quantity > self.max_quantity_per_customer:
            return False
        return self.remaining_quantity >= quantity
    
    def purchase_quantity(self, quantity: int) -> bool:
        """Record a purchase of the specified quantity."""
        if not self.can_purchase_quantity(quantity):
            return False

        self.sold_quantity += quantity

        # Update status if sold out
        if self.remaining_quantity == 0:
            self.status = "ended"

        return True
    
    def update_status(self):
        """Update status based on current time and sales."""
        now = datetime.utcnow()

        if self.status == "cancelled":
            return  # Don't change cancelled status

        if now < self.start_time:
            self.status = "scheduled"
        elif now > self.end_time or self.remaining_quantity == 0:
            self.status = "ended"
        else:
            self.status = "active"
    
    def __str__(self):
        return f"{self.name} ({self.status})"

    def __repr__(self):
        return f"<FlashSaleCampaign(id={self.id}, name='{self.name}', spu_id='{self.spu_id}', status='{self.status}')>"
