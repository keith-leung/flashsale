"""SPU model (Variant Z)."""

from sqlalchemy import Column, String, Boolean, DateTime, func

from app.core.database import Base


class SPU(Base):
    """Standard Product Unit model."""
    __tablename__ = 'spus'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(250), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(String(1000), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())