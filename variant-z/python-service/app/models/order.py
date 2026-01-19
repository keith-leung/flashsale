"""Order model (Variant Z)."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Enum as SQLEnum, func

from app.core.database import Base


class Order(Base):
    """Order model."""
    __tablename__ = 'orders'
    
    id = Column(String(36), primary_key=True)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    shipping_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    status = Column(SQLEnum('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'), nullable=False, default='pending', index=True)
    notes = Column(String(1000), nullable=True)
    flash_sale_campaign_id = Column(String(36), ForeignKey('flash_sale_campaigns.id'), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())