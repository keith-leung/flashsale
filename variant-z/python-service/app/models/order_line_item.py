"""Order Line Item model (Variant Z)."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric, func

from app.core.database import Base


class OrderLineItem(Base):
    """Order Line Item model."""
    __tablename__ = 'order_line_items'
    
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False, index=True)
    sku_id = Column(String(36), ForeignKey('skus.id'), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    product_name = Column(String(255), nullable=False)
    sku_code = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())