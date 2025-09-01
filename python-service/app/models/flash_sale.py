"""Flash Sale Event model."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class FlashSaleStatus(str, Enum):
    """Flash sale status enumeration."""
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class FlashSaleEvent(Base):
    """Flash Sale Event with time-based controls and sale limits."""
    
    __tablename__ = "flash_sale_events"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(250), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Foreign Keys
    sku_id = Column(CHAR(36), ForeignKey("skus.id"), nullable=False, index=True)
    
    # Sale constraints
    total_sale_limit = Column(Integer, nullable=False)  # Total units available for this flash sale
    sold_quantity = Column(Integer, default=0, nullable=False)  # Units sold so far
    max_quantity_per_customer = Column(Integer, default=1, nullable=False)  # Max per customer
    
    # Time constraints
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    
    # Status and flags
    status = Column(SQLEnum(FlashSaleStatus), default=FlashSaleStatus.SCHEDULED, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sku = relationship("SKU")
    orders = relationship("Order", back_populates="flash_sale")
    
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
            and self.status == FlashSaleStatus.ACTIVE
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
            self.status = FlashSaleStatus.ENDED
            
        return True
    
    def update_status(self):
        """Update status based on current time and sales."""
        now = datetime.utcnow()
        
        if self.status == FlashSaleStatus.CANCELLED:
            return  # Don't change cancelled status
        
        if now < self.start_time:
            self.status = FlashSaleStatus.SCHEDULED
        elif now > self.end_time or self.remaining_quantity == 0:
            self.status = FlashSaleStatus.ENDED
        else:
            self.status = FlashSaleStatus.ACTIVE
    
    def __str__(self):
        return f"{self.name} ({self.status.value})"
    
    def __repr__(self):
        return f"<FlashSaleEvent(id={self.id}, name='{self.name}', status='{self.status.value}')>"
