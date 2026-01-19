"""Inventory model (Variant Z)."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, func

from app.core.database import Base


class Inventory(Base):
    """Inventory model."""
    __tablename__ = 'inventory'
    
    id = Column(String(36), primary_key=True)
    sku_id = Column(String(36), ForeignKey('skus.id'), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)
    allow_negative_stock = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())