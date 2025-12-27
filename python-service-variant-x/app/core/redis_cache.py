"""Redis caching layer for Variant X (Redis-Only Architecture)."""

import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache manager for SKU and Inventory data."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 300  # 5 minutes default TTL
        self.sku_ttl = 600  # 10 minutes for SKU data (changes infrequently)
        self.inventory_ttl = 60  # 1 minute for inventory (changes frequently during flash sales)

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100
            )
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.redis_client:
            return False

        try:
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def get_sku(self, sku_id: str) -> Optional[Dict[str, Any]]:
        """Get SKU data from cache."""
        return await self.get(f"sku:{sku_id}")

    async def set_sku(self, sku_id: str, sku_data: Dict[str, Any]) -> bool:
        """Set SKU data in cache."""
        return await self.set(f"sku:{sku_id}", sku_data, self.sku_ttl)

    async def get_inventory(self, sku_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory data from cache."""
        return await self.get(f"inventory:{sku_id}")

    async def set_inventory(self, sku_id: str, inventory_data: Dict[str, Any]) -> bool:
        """Set inventory data in cache."""
        return await self.set(f"inventory:{sku_id}", inventory_data, self.inventory_ttl)

    async def invalidate_sku(self, sku_id: str) -> bool:
        """Invalidate SKU cache."""
        return await self.delete(f"sku:{sku_id}")

    async def invalidate_inventory(self, sku_id: str) -> bool:
        """Invalidate inventory cache."""
        return await self.delete(f"inventory:{sku_id}")

    async def get_multi_sku(self, sku_ids: list[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple SKUs from cache (pipeline for efficiency)."""
        if not self.redis_client or not sku_ids:
            return {}

        try:
            pipe = self.redis_client.pipeline()
            for sku_id in sku_ids:
                pipe.get(f"sku:{sku_id}")

            results = await pipe.execute()

            output = {}
            for sku_id, value in zip(sku_ids, results):
                if value:
                    output[sku_id] = json.loads(value)
                    logger.debug(f"Cache HIT: sku:{sku_id}")
                else:
                    output[sku_id] = None
                    logger.debug(f"Cache MISS: sku:{sku_id}")

            return output
        except Exception as e:
            logger.error(f"Redis MGET error: {e}")
            return {sku_id: None for sku_id in sku_ids}


# Global cache instance
cache = RedisCache()


async def get_cache() -> RedisCache:
    """Dependency to get Redis cache instance."""
    return cache
