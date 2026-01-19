"""SKU model (Variant Z)."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, func

from app.core.database import Base


class SKU(Base):
    """Stock Keeping Unit model."""
    __tablename__ = 'skus'
    
    id = Column(String(36), primary_key=True)
    sku_code = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)
    spu_id = Column(String(36), ForeignKey('spus.id'), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(8, 3), nullable=True)
    track_inventory = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())