"""Payment model (Variant Z)."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Enum as SQLEnum, func

from app.core.database import Base


class Payment(Base):
    """Payment model."""
    __tablename__ = 'payments'
    
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    payment_method = Column(String(50), nullable=False)
    gateway_transaction_id = Column(String(255), nullable=True)
    gateway_response = Column(String(1000), nullable=True)
    status = Column(SQLEnum('pending', 'authorized', 'captured', 'failed', 'cancelled', 'refunded'), nullable=False, default='pending', index=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())