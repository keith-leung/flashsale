"""Database configuration (WORKABLE IMPLEMENTATION)."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    
    FIX: Don't use context manager to avoid auto-transaction.
    Just create and yield session.
    """
    logger.info("Creating DB session")
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
