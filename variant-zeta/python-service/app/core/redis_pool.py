"""Redis connection pool for Variant Zeta."""

import logging
from typing import Optional
from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.connection import Connection

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            max_connections=500,  # Pool size for 16 workers
            decode_responses=True
        )
        logger.info(f"Created Redis connection pool (max_connections=500)")
    
    return _redis_pool


async def get_redis() -> Redis:
    """Get Redis client from pool."""
    global _redis_client
    
    if _redis_client is None:
        pool = await get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
        logger.info("Created Redis client from connection pool")
    
    return _redis_client


async def close_redis():
    """Close Redis connections."""
    global _redis_pool, _redis_client
    
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Closed Redis client")
    
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Closed Redis connection pool")
