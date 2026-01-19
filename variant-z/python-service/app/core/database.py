"""Database configuration for Variant Z."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315"
)

# Create async engine (optimized for high concurrency)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_size=50,  # Increased from 20
    max_overflow=100,  # Increased from 40
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,  # Add timeout
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection."""
    # Test connection
    async with async_session_maker() as session:
        await session.execute("SELECT 1")