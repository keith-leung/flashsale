"""
Campaign Memory Allocator - Variant A Core Implementation

This module implements the dual-layer tracking system:
- Layer 1: SPU-level campaign counter (shared across all SKUs)
- Layer 2: SKU-level inventory caches (per individual SKU)

Key Design:
- Preallocated items stay in service node memory (99%+ zero network I/O)
- Async refill from Redis when cache drops below watermark
- Requests NOT blocked during refill (careful state synchronization)
- Fragmentation allowed (write back to DB after campaign ends)
"""

import asyncio
import logging
import time
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class SKUCache:
    """Per-SKU inventory cache with refill control"""
    sku_id: str
    local_cache: int
    refill_watermark: int
    lock: asyncio.Lock
    refill_in_progress: bool = False
    last_refill_time: float = 0.0
    total_served: int = 0  # Metrics


@dataclass
class CampaignMemory:
    """Memory allocation for a single campaign"""
    campaign_id: str
    spu_id: str
    flash_price: float
    ordinary_price: float

    # Layer 1: SPU-level counter (shared across all SKUs)
    spu_counter: int
    spu_lock: asyncio.Lock

    # Layer 2: SKU-level caches (per SKU variant)
    sku_caches: Dict[str, SKUCache]

    # Status tracking
    status: str = "active"  # active, exhausted, closed
    exhausted_at: Optional[float] = None

    # Metrics
    total_orders: int = 0
    redis_refills: int = 0


class CampaignMemoryAllocator:
    """
    Manages preallocated memory for flash sale campaigns

    Each service instance (Python/Java/C#) maintains its own allocator
    with its share of preallocated items based on performance ratio.
    """

    # Refill configuration
    REFILL_BATCH_SIZE = 500
    REFILL_TIMEOUT_MS = 50  # Max wait time for refill to complete
    REFILL_COOLDOWN_MS = 100  # Minimum time between refills

    def __init__(self, redis_client: redis.Redis, service_name: str = "python"):
        """
        Initialize allocator for this service instance

        Args:
            redis_client: Async Redis client for fallback/refill
            service_name: Service identifier (python, java, csharp)
        """
        self._redis = redis_client
        self._service_name = service_name
        self._campaigns: Dict[str, CampaignMemory] = {}
        self._init_lock = asyncio.Lock()

        logger.info(f"CampaignMemoryAllocator initialized for {service_name}")

    async def load_campaign(
        self,
        campaign_id: str,
        spu_id: str,
        sku_allocations: Dict[str, int],  # {sku_id: allocated_items}
        flash_price: float,
        ordinary_price: float,
        refill_watermark_pct: float = 25.0
    ):
        """
        Load a campaign into memory with preallocated items

        Args:
            campaign_id: Campaign UUID
            spu_id: SPU UUID
            sku_allocations: Dict of SKU IDs to allocated item counts
            flash_price: Flash sale price
            ordinary_price: Regular price (for fallback)
            refill_watermark_pct: Percentage threshold to trigger refill
        """
        async with self._init_lock:
            if campaign_id in self._campaigns:
                logger.warning(f"Campaign {campaign_id} already loaded")
                return

            # Calculate SPU counter (sum of all SKU allocations)
            spu_counter = sum(sku_allocations.values())

            # Create SKU caches
            sku_caches = {}
            for sku_id, allocated in sku_allocations.items():
                watermark = int(allocated * refill_watermark_pct / 100)
                sku_caches[sku_id] = SKUCache(
                    sku_id=sku_id,
                    local_cache=allocated,
                    refill_watermark=watermark,
                    lock=asyncio.Lock()
                )

            # Create campaign memory
            campaign = CampaignMemory(
                campaign_id=campaign_id,
                spu_id=spu_id,
                flash_price=flash_price,
                ordinary_price=ordinary_price,
                spu_counter=spu_counter,
                spu_lock=asyncio.Lock(),
                sku_caches=sku_caches
            )

            self._campaigns[campaign_id] = campaign

            logger.info(
                f"Campaign {campaign_id} loaded: "
                f"SPU counter={spu_counter}, "
                f"SKUs={len(sku_caches)}, "
                f"flash_price={flash_price}, "
                f"ordinary_price={ordinary_price}"
            )

    async def reserve_item(
        self,
        campaign_id: str,
        sku_id: str
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Reserve one item with dual-layer checking

        Flow:
        1. Check SPU counter (campaign-level limit)
        2. Check SKU cache (SKU-level inventory)
        3. Trigger async refill if below watermark
        4. Return (success, price_type, price)

        Returns:
            Tuple of (success, price_type, price)
            - success: True if reserved, False if sold out
            - price_type: "flash", "ordinary", or "sold_out"
            - price: Float price or None
        """
        campaign = self._campaigns.get(campaign_id)

        if not campaign:
            logger.error(f"Campaign {campaign_id} not loaded")
            return (False, "error", None)

        if campaign.status == "closed":
            # Campaign manually closed, use ordinary price
            return (False, "ordinary", campaign.ordinary_price)

        # ========================================
        # LAYER 1: SPU-level campaign counter check
        # ========================================
        async with campaign.spu_lock:
            if campaign.spu_counter <= 0:
                # SPU counter exhausted, try Redis pool
                refilled = await self._try_refill_spu_from_redis(campaign_id)

                if not refilled:
                    # Campaign truly exhausted
                    if campaign.status != "exhausted":
                        campaign.status = "exhausted"
                        campaign.exhausted_at = time.time()
                        logger.warning(
                            f"Campaign {campaign_id} EXHAUSTED "
                            f"(SPU counter depleted)"
                        )

                    # Return ordinary price (fallback to DB)
                    return (False, "ordinary", campaign.ordinary_price)

            # Decrement SPU counter (tentative)
            campaign.spu_counter -= 1
            spu_reserved = True

        # ========================================
        # LAYER 2: SKU-level cache check
        # ========================================
        sku_cache = campaign.sku_caches.get(sku_id)

        if not sku_cache:
            # SKU not in this service's allocation
            logger.warning(f"SKU {sku_id} not allocated to this service")
            # Rollback SPU counter
            async with campaign.spu_lock:
                campaign.spu_counter += 1
            return (False, "not_allocated", None)

        # Try to reserve from SKU cache
        async with sku_cache.lock:
            if sku_cache.local_cache <= 0:
                # SKU cache empty

                # If refill in progress, wait briefly
                if sku_cache.refill_in_progress:
                    await self._wait_for_refill(sku_cache)

                # Check again after wait
                if sku_cache.local_cache <= 0:
                    # Still empty, try one-time refill
                    refilled = await self._try_refill_sku_from_redis_sync(
                        campaign_id, sku_id, sku_cache
                    )

                    if not refilled or sku_cache.local_cache <= 0:
                        # SKU truly exhausted
                        logger.warning(
                            f"SKU {sku_id} exhausted in campaign {campaign_id}"
                        )

                        # Rollback SPU counter
                        async with campaign.spu_lock:
                            campaign.spu_counter += 1

                        return (False, "sold_out", None)

            # Reserve from SKU cache
            sku_cache.local_cache -= 1
            sku_cache.total_served += 1

            # Check if refill needed (async, non-blocking)
            if (
                sku_cache.local_cache <= sku_cache.refill_watermark
                and not sku_cache.refill_in_progress
            ):
                # Trigger async refill (fire and forget)
                asyncio.create_task(
                    self._async_refill_sku_from_redis(campaign_id, sku_id)
                )

        # Success!
        campaign.total_orders += 1
        return (True, "flash", campaign.flash_price)

    async def _try_refill_spu_from_redis(self, campaign_id: str) -> bool:
        """
        Try to refill SPU counter from Redis pool

        IMPORTANT: Must be called while holding campaign.spu_lock

        Returns:
            True if refilled, False if Redis pool exhausted
        """
        redis_key = f"fs:{campaign_id}:redis_pool:spu_counter"

        try:
            # Try to get a batch from Redis
            current = await self._redis.get(redis_key)

            if current is None or int(current) <= 0:
                return False

            # Decrement Redis (atomic)
            batch_size = min(self.REFILL_BATCH_SIZE, int(current))
            new_value = await self._redis.decrby(redis_key, batch_size)

            if new_value < 0:
                # Went negative, rollback
                await self._redis.incrby(redis_key, batch_size)
                return False

            # Add to SPU counter (lock already held by caller)
            campaign = self._campaigns[campaign_id]
            campaign.spu_counter += batch_size
            campaign.redis_refills += 1

            logger.info(
                f"[SPU REFILL] Campaign {campaign_id}: "
                f"+{batch_size} items from Redis (SPU counter now: {campaign.spu_counter})"
            )

            return True

        except Exception as e:
            logger.error(f"SPU refill failed: {e}", exc_info=True)
            return False

    async def _try_refill_sku_from_redis_sync(
        self,
        campaign_id: str,
        sku_id: str,
        sku_cache: SKUCache
    ) -> bool:
        """
        Synchronous refill attempt (blocking, used when cache is empty)

        Returns:
            True if refilled, False otherwise
        """
        redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"

        try:
            current = await self._redis.get(redis_key)

            if current is None or int(current) <= 0:
                return False

            batch_size = min(self.REFILL_BATCH_SIZE, int(current))
            new_value = await self._redis.decrby(redis_key, batch_size)

            if new_value < 0:
                await self._redis.incrby(redis_key, batch_size)
                return False

            # Add to cache (already holding lock)
            sku_cache.local_cache += batch_size
            sku_cache.last_refill_time = time.time()

            logger.info(
                f"Refilled SKU {sku_id} in campaign {campaign_id}: "
                f"+{batch_size} items from Redis"
            )

            return True

        except Exception as e:
            logger.error(f"SKU refill failed: {e}", exc_info=True)
            return False

    async def _async_refill_sku_from_redis(
        self,
        campaign_id: str,
        sku_id: str
    ):
        """
        Async refill task (triggered when below watermark)

        This runs in background while requests continue to be served.
        Careful state synchronization to avoid race conditions.
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return

        sku_cache = campaign.sku_caches.get(sku_id)
        if not sku_cache:
            return

        # Check cooldown (avoid refill spam)
        now = time.time()
        if now - sku_cache.last_refill_time < self.REFILL_COOLDOWN_MS / 1000:
            return

        # Acquire lock to set refill flag
        async with sku_cache.lock:
            if sku_cache.refill_in_progress:
                return  # Another task already refilling

            # Double-check still needed
            if sku_cache.local_cache > sku_cache.refill_watermark:
                return

            sku_cache.refill_in_progress = True

        try:
            # Refill from Redis (outside lock - requests continue!)
            redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"

            current = await self._redis.get(redis_key)

            if current and int(current) > 0:
                batch_size = min(self.REFILL_BATCH_SIZE, int(current))
                new_value = await self._redis.decrby(redis_key, batch_size)

                if new_value >= 0:
                    # Successfully fetched, add to cache
                    async with sku_cache.lock:
                        sku_cache.local_cache += batch_size
                        sku_cache.last_refill_time = time.time()

                    logger.info(
                        f"[ASYNC] Refilled SKU {sku_id}: +{batch_size} items"
                    )
                else:
                    # Rollback
                    await self._redis.incrby(redis_key, batch_size)

        finally:
            # Clear refill flag
            async with sku_cache.lock:
                sku_cache.refill_in_progress = False

    async def _wait_for_refill(self, sku_cache: SKUCache):
        """
        Wait briefly for ongoing refill to complete

        Args:
            sku_cache: SKU cache with refill in progress
        """
        timeout = self.REFILL_TIMEOUT_MS / 1000
        start = time.time()

        while sku_cache.refill_in_progress and (time.time() - start) < timeout:
            await asyncio.sleep(0.01)  # 10ms sleep

    async def close_campaign(self, campaign_id: str):
        """
        Manually close a campaign (by operator/tester)

        Args:
            campaign_id: Campaign to close
        """
        campaign = self._campaigns.get(campaign_id)
        if campaign:
            campaign.status = "closed"
            logger.info(f"Campaign {campaign_id} manually closed")

    def get_campaign_status(self, campaign_id: str) -> Optional[Dict]:
        """
        Get current status and metrics for a campaign

        Returns:
            Dict with status, counters, and metrics
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        sku_status = {}
        for sku_id, cache in campaign.sku_caches.items():
            sku_status[sku_id] = {
                "local_cache": cache.local_cache,
                "watermark": cache.refill_watermark,
                "refilling": cache.refill_in_progress,
                "total_served": cache.total_served
            }

        return {
            "campaign_id": campaign_id,
            "status": campaign.status,
            "spu_counter": campaign.spu_counter,
            "sku_caches": sku_status,
            "total_orders": campaign.total_orders,
            "redis_refills": campaign.redis_refills,
            "exhausted_at": campaign.exhausted_at
        }
