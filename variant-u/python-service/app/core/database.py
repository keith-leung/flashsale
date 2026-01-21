"""Database configuration and setup."""

import logging
import os
import sys
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection pool configuration
# With 16 workers (fixed for 8 CPU allocation), we need sufficient connections per worker
# Formula: max_workers * (pool_size + max_overflow) < mariadb_max_connections
# Example: 16 workers * (10 + 5) = 240 connections (safe for max_connections=3000)

if os.getenv("TESTING") or "pytest" in sys.modules:
    # Use NullPool for testing to avoid connection sharing across event loops
    pool_class = NullPool
    pool_kwargs = {}
else:
    # For production: use default async pool with strict limits
    # AsyncEngine uses AsyncAdaptedQueuePool by default (async-safe)
    pool_class = None  # Let async engine use its default pool
    pool_kwargs = {
        "pool_size": 10,             # 10 connections per worker (16 workers = 160 base)
        "max_overflow": 5,           # Allow 5 extra per worker (16 workers = 80 extra)
        "pool_timeout": 30.0,        # Wait up to 30s for connection
        "pool_recycle": 3600,        # Recycle connections after 1 hour
        "pool_pre_ping": True,       # Verify connections before use
    }

# Create async engine
if pool_class is None:
    # Use default async pool with configuration
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        isolation_level="READ COMMITTED",
        **pool_kwargs
    )
else:
    # Use NullPool for testing
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
