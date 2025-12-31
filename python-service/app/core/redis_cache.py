import os
import json
import logging
from typing import List, Optional, Any, Dict, Union
from uuid import UUID

import redis.asyncio as redis
from app.models.sku import SKU

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self.sku_ttl = 600  # 10 minutes
        self.inventory_ttl = 60   # 1 minute

    async def connect(self):
        if not self.client:
            self.client = redis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def close(self):
        if self.client:
            await self.client.close()
            logger.info("Closed Redis connection")

    def _get_sku_key(self, sku_id: Union[str, UUID]) -> str:
        return f"sku:{str(sku_id)}"

    async def get_multi_sku(self, sku_ids: List[Union[str, UUID]]) -> Dict[str, Any]:
        """Batch fetch SKUs from Redis using pipeline."""
        if not self.client or not sku_ids:
            return {}

        pipeline = self.client.pipeline()
        keys = [self._get_sku_key(sid) for sid in sku_ids]
        
        for key in keys:
            pipeline.get(key)
        
        results = await pipeline.execute()
        
        cached_skus = {}
        for i, result in enumerate(results):
            if result:
                try:
                    data = json.loads(result)
                    cached_skus[str(sku_ids[i])] = data
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode cache for SKU {sku_ids[i]}")
        
        return cached_skus

    async def set_multi_sku(self, skus_data: Dict[str, Any]):
        """Batch cache SKUs."""
        if not self.client or not skus_data:
            return

        pipeline = self.client.pipeline()
        for sku_id, data in skus_data.items():
            key = self._get_sku_key(sku_id)
            pipeline.set(key, json.dumps(data), ex=self.sku_ttl)
        
        await pipeline.execute()

    async def invalidate_sku(self, sku_id: Union[str, UUID]):
        if self.client:
            await self.client.delete(self._get_sku_key(sku_id))

    @staticmethod
    def serialize_sku(sku: SKU) -> Dict[str, Any]:
        """Serialize SKU entity for caching."""
        data = {
            "id": str(sku.id),
            "sku_code": sku.sku_code,
            "price": float(sku.price),
            "track_inventory": sku.track_inventory,
            "is_active": sku.is_active,
            "spu_name": sku.spu.name if sku.spu else (sku.name or "Product"),
        }

        if sku.inventory:
            data.update({
                "quantity": sku.inventory.quantity,
                "reserved_quantity": sku.inventory.reserved_quantity,
                "allow_negative_stock": sku.inventory.allow_negative_stock
            })
        else:
            data.update({
                "quantity": 0,
                "reserved_quantity": 0,
                "allow_negative_stock": False
            })

        return data

    # ============================================================
    # Flash Sale Campaign Methods (Variant X)
    # ============================================================

    def _get_campaign_limit_key(self, flash_sale_id: Union[str, UUID]) -> str:
        """Get Redis key for campaign limit counter."""
        return f"fs:{str(flash_sale_id)}:limit"

    def _get_campaign_meta_key(self, flash_sale_id: Union[str, UUID]) -> str:
        """Get Redis key for campaign metadata."""
        return f"fs:{str(flash_sale_id)}:meta"

    def _get_inventory_key(self, sku_id: Union[str, UUID]) -> str:
        """Get Redis key for SKU inventory counter."""
        return f"inv:{str(sku_id)}"

    def _get_sku_meta_key(self, sku_id: Union[str, UUID]) -> str:
        """Get Redis key for SKU metadata."""
        return f"sku:{str(sku_id)}:meta"

    async def reserve_campaign_inventory(self, flash_sale_id: Union[str, UUID], quantity: int) -> int:
        """
        Atomically reserve inventory from campaign limit.
        Returns new remaining quantity (negative if oversold).
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        key = self._get_campaign_limit_key(flash_sale_id)
        new_value = await self.client.decrby(key, quantity)
        return new_value

    async def release_campaign_inventory(self, flash_sale_id: Union[str, UUID], quantity: int):
        """Release (rollback) campaign inventory reservation."""
        if not self.client:
            return

        key = self._get_campaign_limit_key(flash_sale_id)
        await self.client.incrby(key, quantity)

    async def reserve_sku_inventory(self, sku_id: Union[str, UUID], quantity: int) -> int:
        """
        Atomically reserve inventory from SKU level.
        Returns new remaining quantity (negative if oversold).
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        key = self._get_inventory_key(sku_id)
        new_value = await self.client.decrby(key, quantity)
        return new_value

    async def release_sku_inventory(self, sku_id: Union[str, UUID], quantity: int):
        """Release (rollback) SKU inventory reservation."""
        if not self.client:
            return

        key = self._get_inventory_key(sku_id)
        await self.client.incrby(key, quantity)

    async def get_campaign_meta(self, flash_sale_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get campaign metadata from Redis."""
        if not self.client:
            return None

        key = self._get_campaign_meta_key(flash_sale_id)
        result = await self.client.hgetall(key)
        return dict(result) if result else None

    async def set_campaign_meta(self, flash_sale_id: Union[str, UUID], metadata: Dict[str, Any]):
        """Set campaign metadata in Redis."""
        if not self.client:
            return

        key = self._get_campaign_meta_key(flash_sale_id)
        await self.client.hset(key, mapping=metadata)

    async def get_campaign_limit(self, flash_sale_id: Union[str, UUID]) -> Optional[int]:
        """Get current campaign limit remaining."""
        if not self.client:
            return None

        key = self._get_campaign_limit_key(flash_sale_id)
        result = await self.client.get(key)
        return int(result) if result is not None else None

    async def set_campaign_limit(self, flash_sale_id: Union[str, UUID], limit: int):
        """Set campaign limit counter."""
        if not self.client:
            return

        key = self._get_campaign_limit_key(flash_sale_id)
        await self.client.set(key, limit)

    async def get_sku_meta(self, sku_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get SKU metadata from Redis."""
        if not self.client:
            return None

        key = self._get_sku_meta_key(sku_id)
        result = await self.client.hgetall(key)
        return dict(result) if result else None

    async def batch_get_sku_meta(self, sku_ids: List[Union[str, UUID]]) -> Dict[str, Dict[str, Any]]:
        """Batch fetch SKU metadata using pipeline."""
        if not self.client or not sku_ids:
            return {}

        pipeline = self.client.pipeline()
        for sku_id in sku_ids:
            pipeline.hgetall(self._get_sku_meta_key(sku_id))

        results = await pipeline.execute()

        metadata = {}
        for i, result in enumerate(results):
            if result:
                metadata[str(sku_ids[i])] = dict(result)

        return metadata

    async def set_sku_meta(self, sku_id: Union[str, UUID], metadata: Dict[str, Any], ttl: int = 600):
        """Set SKU metadata in Redis with TTL."""
        if not self.client:
            return

        key = self._get_sku_meta_key(sku_id)
        await self.client.hset(key, mapping=metadata)
        await self.client.expire(key, ttl)

    async def queue_order(self, order_data: Dict[str, Any], stream_name: str = "order_queue"):
        """Add order to Redis Stream for async persistence."""
        if not self.client:
            raise RuntimeError("Redis client not connected")

        await self.client.xadd(stream_name, order_data)

# Global instance
redis_cache = RedisCache()
