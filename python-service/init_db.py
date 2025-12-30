#!/usr/bin/env python3
"""Initialize database schema."""

import asyncio
import os

# Set DATABASE_URL
os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'mysql+aiomysql://root:root@10.88.0.2:3306/orange315')

from app.core.database import engine, Base  # noqa: E402
# Import all models to register them with Base.metadata
from app.models import flash_sale, inventory, order, sku, spu  # noqa: E402, F401


async def init_database():
    """Create all database tables."""
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database initialized successfully")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
