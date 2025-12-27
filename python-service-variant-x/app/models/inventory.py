"""Inventory model for tracking stock levels."""

import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, DateTime, Boolean
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class Inventory(Base):
    """Inventory tracking for SKUs."""
    
    __tablename__ = "inventory"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    sku_id = Column(CHAR(36), ForeignKey("skus.id"), nullable=False, unique=True, index=True)
    
    # Stock levels
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)  # Items in pending orders
    
    # Stock management
    allow_negative_stock = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sku = relationship("SKU", back_populates="inventory")
    
    @property
    def available_quantity(self):
        """Calculate available quantity (total - reserved)."""
        return max(0, self.quantity - self.reserved_quantity)
    
    def can_fulfill_quantity(self, requested_quantity: int) -> bool:
        """Check if the requested quantity can be fulfilled."""
        if self.allow_negative_stock:
            return True
        return self.available_quantity >= requested_quantity
    
    def reserve_quantity(self, quantity: int) -> bool:
        """Reserve quantity for an order."""
        if not self.can_fulfill_quantity(quantity):
            return False
        self.reserved_quantity += quantity
        return True
    
    def release_quantity(self, quantity: int):
        """Release reserved quantity back to available stock."""
        self.reserved_quantity = max(0, self.reserved_quantity - quantity)
    
    def fulfill_quantity(self, quantity: int) -> bool:
        """Fulfill an order by reducing both reserved and total quantity."""
        if self.reserved_quantity < quantity:
            return False
        self.reserved_quantity -= quantity
        self.quantity -= quantity
        return True
    
    def __str__(self):
        return f"Inventory for {self.sku.sku_code}: {self.available_quantity}/{self.quantity}"
    
    def __repr__(self):
        return f"<Inventory(sku_id={self.sku_id}, quantity={self.quantity}, reserved={self.reserved_quantity})>"
