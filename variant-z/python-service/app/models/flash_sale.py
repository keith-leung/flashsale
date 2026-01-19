"""Flash Sale Campaign model (Variant Z)."""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Enum as SQLEnum, func

from app.core.database import Base


class FlashSaleCampaign(Base):
    """Flash Sale Campaign model."""
    __tablename__ = 'flash_sale_campaigns'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(1000), nullable=True)
    spu_id = Column(String(36), ForeignKey('spus.id'), nullable=False, index=True)
    total_sale_limit = Column(Integer, nullable=False)
    sold_quantity = Column(Integer, nullable=False, default=0)
    max_quantity_per_customer = Column(Integer, nullable=False, default=1)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum('scheduled', 'active', 'ended', 'cancelled'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())