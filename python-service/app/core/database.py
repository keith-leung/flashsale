"""Database configuration and setup."""

import logging
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use NullPool for testing to avoid connection sharing across event loops
pool_class = NullPool if os.getenv("TESTING") or "pytest" in sys.modules else None

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    isolation_level="READ COMMITTED",
    poolclass=pool_class,
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
    """Dependency to get database session."""
    logger.info("Creating DB session with READ COMMITTED isolation level.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
