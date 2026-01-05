"""Stock Keeping Unit (SKU) model."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Integer, Numeric
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class SKU(Base):
    """Stock Keeping Unit - represents a specific variant of a product (like Saleor's ProductVariant)."""
    
    __tablename__ = "skus"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku_code = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    
    # Foreign Keys
    spu_id = Column(CHAR(36), ForeignKey("spus.id"), nullable=False, index=True)
    
    # Product details
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    cost_price = Column(Numeric(precision=10, scale=2), nullable=True)
    weight = Column(Numeric(precision=8, scale=3), nullable=True)  # in kg
    
    # Inventory tracking
    track_inventory = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    spu = relationship("SPU", back_populates="skus")
    inventory = relationship("Inventory", back_populates="sku", uselist=False, cascade="all, delete-orphan")
    
    def __str__(self):
        return self.sku_code or f"SKU-{self.id}"
    
    def __repr__(self):
        return f"<SKU(id={self.id}, sku_code='{self.sku_code}', spu_id={self.spu_id})>"
