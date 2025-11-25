"""Standard Product Unit (SPU) model."""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Column, String, Text, DateTime, Boolean, Float
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class SPU(Base):
    """Standard Product Unit - represents a product concept (like Saleor's Product)."""
    
    __tablename__ = "spus"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(250), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    skus = relationship("SKU", back_populates="spu", cascade="all, delete-orphan")
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"<SPU(id={self.id}, name='{self.name}')>"
