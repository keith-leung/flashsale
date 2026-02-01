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
- Lua scripts for atomic Redis operations (zero overselling guarantee)
"""

import asyncio
import logging
import os
import time
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Lua script paths
LUA_SCRIPT_DIR = os.path.join(os.path.dirname(__file__), '..', 'lua')


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

    # Refill configuration (optimized for Big Business - Gemini's recommendation)
    # Key insight: Coalesce requests to wait for ONE batch refill instead of
    # each doing individual Redis I/O (which saturates the event loop).
    REFILL_BATCH_SIZE = 100000  # Large batches for sustained high RPS
    REFILL_TIMEOUT_MS = 200     # Wait up to 200ms for batch refill to complete
    REFILL_COOLDOWN_MS = 1      # Minimal cooldown for aggressive refill
    HIGH_WATERMARK_PCT = 70     # Trigger refill when 70% of initial allocation remains

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
        self._sku_to_campaign: Dict[str, str] = {}  # Reverse index: SKU -> Campaign
        self._init_lock = asyncio.Lock()

        # Order queue for fire-and-forget persistence
        self._order_queue: asyncio.Queue = asyncio.Queue()
        self._order_flusher_task: Optional[asyncio.Task] = None

        # Lua script SHAs (loaded lazily on first use)
        self._refill_batch_sha: Optional[str] = None
        self._reserve_single_sha: Optional[str] = None
        self._lua_loaded = False

        # Proactive refill loop (Gemini's recommendation)
        self._proactive_refill_task: Optional[asyncio.Task] = None

        logger.info(f"CampaignMemoryAllocator initialized for {service_name}")

    def get_campaign_for_sku(self, sku_id: str) -> Optional[str]:
        """
        O(1) lookup: Check if SKU is in a loaded campaign
        Returns campaign_id if found and active, None otherwise.
        Use this instead of Redis meta lookup.
        """
        campaign_id = self._sku_to_campaign.get(sku_id)
        if campaign_id:
            campaign = self._campaigns.get(campaign_id)
            if campaign and campaign.status == "active":
                return campaign_id
        return None

    async def queue_order_fire_and_forget(self, order_data: dict):
        """
        Queue order for async write-back (ZERO BLOCKING).
        Orders are batched and written to Redis in background.
        Mirrors C#'s QueueOrderFireAndForget()
        """
        try:
            self._order_queue.put_nowait(order_data)
        except asyncio.QueueFull:
            # Queue full, force flush
            await self._flush_order_queue()
            self._order_queue.put_nowait(order_data)

        # Start flusher if not running
        if self._order_flusher_task is None or self._order_flusher_task.done():
            self._order_flusher_task = asyncio.create_task(self._order_flusher_loop())

    async def _order_flusher_loop(self):
        """Background task to flush order queue to Redis"""
        while True:
            try:
                await asyncio.sleep(0.1)  # 100ms
                await self._flush_order_queue()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Order flush failed: {e}")

    async def _flush_order_queue(self):
        """Flush pending orders to Redis stream"""
        if self._order_queue.empty():
            return

        batch = []
        while not self._order_queue.empty() and len(batch) < 1000:
            try:
                order = self._order_queue.get_nowait()
                batch.append(order)
            except asyncio.QueueEmpty:
                break

        if not batch or self._redis is None:
            return

        try:
            import json
            for order_data in batch:
                await self._redis.xadd("order_queue", {"order_data": json.dumps(order_data)})
            logger.debug(f"Flushed {len(batch)} orders to Redis")
        except Exception as e:
            logger.error(f"Failed to flush orders to Redis: {e}")
            # Re-queue failed orders
            for order in batch:
                try:
                    self._order_queue.put_nowait(order)
                except asyncio.QueueFull:
                    pass

    async def _ensure_lua_scripts_loaded(self):
        """Load Lua scripts into Redis (lazy initialization)"""
        if self._lua_loaded:
            return

        # Bypass for micro-benchmark
        if os.environ.get("BENCHMARK_MODE") == "true":
            self._lua_loaded = True
            return

        async with self._init_lock:
            if self._lua_loaded:
                return

            try:
                # Load refill_batch.lua
                refill_path = os.path.join(LUA_SCRIPT_DIR, 'refill_batch.lua')
                with open(refill_path, 'r') as f:
                    self._refill_batch_sha = await self._redis.script_load(f.read())

                # Load reserve_single.lua
                reserve_path = os.path.join(LUA_SCRIPT_DIR, 'reserve_single.lua')
                with open(reserve_path, 'r') as f:
                    self._reserve_single_sha = await self._redis.script_load(f.read())

                self._lua_loaded = True
                logger.info(
                    f"Lua scripts loaded: refill_batch={self._refill_batch_sha[:8]}..., "
                    f"reserve_single={self._reserve_single_sha[:8]}..."
                )
            except Exception as e:
                logger.error(f"Failed to load Lua scripts: {e}", exc_info=True)
                raise

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
        # Ensure Lua scripts are loaded
        await self._ensure_lua_scripts_loaded()

        async with self._init_lock:
            if campaign_id in self._campaigns:
                logger.warning(f"Campaign {campaign_id} already loaded")
                return

            # Calculate SPU counter (sum of all SKU allocations)
            spu_counter = sum(sku_allocations.values())

            # Create SKU caches
            # Use HIGH_WATERMARK_PCT (70%) instead of passed parameter
            # This ensures refill triggers early (when 30% consumed, 70% remaining)
            # so the refill completes before buffer empties
            sku_caches = {}
            for sku_id, allocated in sku_allocations.items():
                # Watermark = 70% of initial allocation
                # Refill triggers when local_cache <= watermark (70% remaining)
                watermark = int(allocated * self.HIGH_WATERMARK_PCT / 100)
                sku_caches[sku_id] = SKUCache(
                    sku_id=sku_id,
                    local_cache=allocated,
                    refill_watermark=watermark,
                    lock=asyncio.Lock()
                )
                # Also store initial allocation for metrics
                sku_caches[sku_id].initial_allocation = allocated

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

            # Build reverse lookup: SKU → Campaign (O(1) lookup)
            for sku_id in sku_allocations.keys():
                self._sku_to_campaign[sku_id] = campaign_id

            logger.info(
                f"Campaign {campaign_id} loaded: "
                f"SPU counter={spu_counter}, "
                f"SKUs={len(sku_caches)}, "
                f"flash_price={flash_price}, "
                f"ordinary_price={ordinary_price}, "
                f"watermark={self.HIGH_WATERMARK_PCT}%"
            )

            # Start proactive refill loop (Gemini's recommendation)
            # This keeps buffers topped up BEFORE they empty
            self.start_proactive_refill()

    async def reserve_item(
        self,
        campaign_id: str,
        sku_id: str
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Reserve one item with dual-layer checking (LOCK-FREE like C#)

        Flow:
        1. Quick decrement SPU counter - if negative, try refill
        2. Quick decrement SKU cache - if negative, try refill
        3. Trigger async refill if below watermark (fire-and-forget)
        4. Return (success, price_type, price)

        KEY: Minimizes lock holding time, NO blocking waits

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
        # LAYER 1: SPU-level counter (MINIMAL LOCK)
        # ========================================
        # Quick decrement - only hold lock for the decrement itself
        campaign.spu_counter -= 1
        if campaign.spu_counter < 0:
            # Went negative - restore and try refill
            campaign.spu_counter += 1

            # Try refill (without holding any lock on hot path)
            refilled = await self._try_refill_spu_lockfree(campaign_id)

            if not refilled:
                # Campaign truly exhausted
                if campaign.status != "exhausted":
                    campaign.status = "exhausted"
                    campaign.exhausted_at = time.time()
                    logger.warning(
                        f"Campaign {campaign_id} EXHAUSTED "
                        f"(SPU counter depleted)"
                    )
                return (False, "ordinary", campaign.ordinary_price)

            # Retry decrement after refill
            campaign.spu_counter -= 1
            if campaign.spu_counter < 0:
                campaign.spu_counter += 1
                return (False, "ordinary", campaign.ordinary_price)

        # ========================================
        # LAYER 2: SKU-level cache (MINIMAL LOCK)
        # ========================================
        sku_cache = campaign.sku_caches.get(sku_id)

        if not sku_cache:
            # SKU not in this service's allocation
            logger.warning(f"SKU {sku_id} not allocated to this service")
            # Rollback SPU counter
            campaign.spu_counter += 1
            return (False, "not_allocated", None)

        # Quick decrement - no lock needed in single-threaded asyncio
        sku_cache.local_cache -= 1
        if sku_cache.local_cache < 0:
            # Went negative - restore and try refill
            sku_cache.local_cache += 1

            # Try refill (without blocking)
            refilled = await self._try_refill_sku_lockfree(
                campaign_id, sku_id, sku_cache
            )

            if not refilled:
                # Gemini's fix: Wait for batched refill instead of per-request Redis I/O.
                # In single-threaded Python, individual Redis calls saturate the event loop.
                # Instead, wait briefly for the ONE batch refill operation to complete.
                # This coalesces thousands of requests into waiting for 1 Redis call.

                # Wait for ongoing refill to complete (if any)
                if sku_cache.refill_in_progress:
                    await self._wait_for_refill(sku_cache)
                    # Retry after waiting for refill
                    if sku_cache.local_cache > 0:
                        sku_cache.local_cache -= 1
                        sku_cache.total_served += 1
                        campaign.total_orders += 1
                        return (True, "flash", campaign.flash_price)

                # Refill truly failed (Redis pool empty)
                logger.warning(
                    f"SKU {sku_id} exhausted in campaign {campaign_id} "
                    f"(refill failed, Redis pool empty)"
                )
                campaign.spu_counter += 1  # Rollback SPU
                return (False, "sold_out", None)

            # Retry decrement after refill
            sku_cache.local_cache -= 1
            if sku_cache.local_cache < 0:
                sku_cache.local_cache += 1
                campaign.spu_counter += 1
                return (False, "sold_out", None)

        # Trigger background refill if below watermark (fire-and-forget)
        if (
            sku_cache.local_cache <= sku_cache.refill_watermark
            and not sku_cache.refill_in_progress
        ):
            asyncio.create_task(
                self._async_refill_sku_from_redis(campaign_id, sku_id)
            )

        sku_cache.total_served += 1
        campaign.total_orders += 1
        return (True, "flash", campaign.flash_price)

    async def _try_direct_redis_reserve(self, campaign_id: str, sku_id: str) -> bool:
        """
        Direct Redis fallback - bypass local cache and hit Redis directly.
        Used when local cache is depleted and refill fails.
        Like C#'s HandleDepletedAsync() method.

        WARNING: This method is COUNTERPRODUCTIVE for Python's Big Business mode.
        Unlike C# (multi-threaded TPL) and Java (virtual threads), Python's
        single-threaded event loop saturates when processing per-request Redis I/O.
        This effectively turns the in-memory architecture into per-request Redis,
        limiting throughput to ~700 RPS instead of ~13K RPS.

        For Python, use Small Business mode (100% preallocation) to avoid this path.
        This fallback exists for graceful degradation, not high-throughput operation.

        Returns:
            True if reserved from Redis, False if Redis pool also empty
        """
        if os.environ.get("BENCHMARK_MODE") == "true":
            # In benchmark mode, always succeed for direct reserve
            return True

        if self._redis is None:
            return False

        try:
            redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"
            remaining = await self._redis.decr(redis_key)

            if remaining >= 0:
                # Success! Reserved directly from Redis pool
                logger.debug(f"Direct Redis reserve success: SKU {sku_id}, remaining={remaining}")
                return True
            else:
                # Redis pool also depleted, restore the decrement
                await self._redis.incr(redis_key)
                return False
        except Exception as e:
            logger.error(f"Direct Redis reserve failed: {e}")
            return False

    async def _try_refill_spu_lockfree(self, campaign_id: str) -> bool:
        """
        Lock-free SPU refill using single-flight pattern.

        Uses a flag to ensure only one coroutine refills at a time.
        Other coroutines check counter and return immediately.
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        # Single-flight pattern: only one refill at a time
        if hasattr(campaign, '_spu_refilling') and campaign._spu_refilling:
            # Another coroutine is refilling, just check if counter is positive
            return campaign.spu_counter > 0

        # Mark as refilling (atomic in single-threaded asyncio)
        campaign._spu_refilling = True

        try:
            # Double-check after acquiring flag
            if campaign.spu_counter > 0:
                return True

            if os.environ.get("BENCHMARK_MODE") == "true":
                campaign.spu_counter += self.REFILL_BATCH_SIZE
                campaign.redis_refills += 1
                return True

            redis_key = f"fs:{campaign_id}:redis_pool:spu_counter"
            granted = await self._redis.evalsha(
                self._refill_batch_sha,
                1,
                redis_key,
                self.REFILL_BATCH_SIZE
            )

            granted = int(granted)
            if granted > 0:
                campaign.spu_counter += granted
                campaign.redis_refills += 1
                return True
            return False
        except Exception as e:
            logger.error(f"SPU refill failed: {e}", exc_info=True)
            return False
        finally:
            campaign._spu_refilling = False

    async def _try_refill_sku_lockfree(
        self,
        campaign_id: str,
        sku_id: str,
        sku_cache: SKUCache
    ) -> bool:
        """
        Lock-free SKU refill using single-flight pattern.

        Gemini's insight: When refill is in progress, WAIT for it instead of
        returning immediately. This coalesces thousands of requests waiting
        for ONE batch Redis call, instead of each doing individual Redis I/O.
        """
        # Check cooldown
        now = time.time()
        if now - sku_cache.last_refill_time < self.REFILL_COOLDOWN_MS / 1000:
            return sku_cache.local_cache > 0

        # Single-flight pattern: If refill in progress, WAIT for it
        if sku_cache.refill_in_progress:
            # Wait for the batch refill to complete (Gemini's fix)
            await self._wait_for_refill(sku_cache)
            return sku_cache.local_cache > 0

        sku_cache.refill_in_progress = True

        try:
            # Double-check after acquiring flag
            if sku_cache.local_cache > 0:
                return True

            if os.environ.get("BENCHMARK_MODE") == "true":
                sku_cache.local_cache += self.REFILL_BATCH_SIZE
                sku_cache.last_refill_time = now
                return True

            redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"
            granted = await self._redis.evalsha(
                self._refill_batch_sha,
                1,
                redis_key,
                self.REFILL_BATCH_SIZE
            )

            granted = int(granted)
            if granted > 0:
                sku_cache.local_cache += granted
                sku_cache.last_refill_time = now
                return True
            return False
        except Exception as e:
            logger.error(f"SKU refill failed: {e}", exc_info=True)
            return False
        finally:
            sku_cache.refill_in_progress = False

    async def _try_refill_spu_from_redis(self, campaign_id: str) -> bool:
        """
        Try to refill SPU counter from Redis pool using Lua script (atomic)

        IMPORTANT: Must be called while holding campaign.spu_lock

        Returns:
            True if refilled, False if Redis pool exhausted
        """
        redis_key = f"fs:{campaign_id}:redis_pool:spu_counter"

        if os.environ.get("BENCHMARK_MODE") == "true":
            campaign = self._campaigns[campaign_id]
            campaign.spu_counter += self.REFILL_BATCH_SIZE
            campaign.redis_refills += 1
            return True

        try:
            # Use Lua script for atomic batch refill (zero overselling)
            granted = await self._redis.evalsha(
                self._refill_batch_sha,
                1,  # Number of keys
                redis_key,
                self.REFILL_BATCH_SIZE
            )

            granted = int(granted)

            if granted < 0:
                # Pool exhausted
                return False

            # Add to SPU counter (lock already held by caller)
            campaign = self._campaigns[campaign_id]
            campaign.spu_counter += granted
            campaign.redis_refills += 1

            logger.info(
                f"[SPU REFILL] Campaign {campaign_id}: "
                f"+{granted} items from Redis (SPU counter now: {campaign.spu_counter})"
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
        Synchronous refill attempt using Lua script (atomic, zero overselling)

        Returns:
            True if refilled, False otherwise
        """
        redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"

        if os.environ.get("BENCHMARK_MODE") == "true":
            sku_cache.local_cache += self.REFILL_BATCH_SIZE
            sku_cache.last_refill_time = time.time()
            return True

        try:
            # Use Lua script for atomic batch refill (zero overselling)
            granted = await self._redis.evalsha(
                self._refill_batch_sha,
                1,  # Number of keys
                redis_key,
                self.REFILL_BATCH_SIZE
            )

            granted = int(granted)

            if granted < 0:
                # Pool exhausted
                return False

            # Add to cache (already holding lock)
            sku_cache.local_cache += granted
            sku_cache.last_refill_time = time.time()

            logger.info(
                f"Refilled SKU {sku_id} in campaign {campaign_id}: "
                f"+{granted} items from Redis"
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
            # Refill from Redis using Lua script (atomic, zero overselling)
            redis_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"

            # Use Lua script for atomic batch refill
            granted = await self._redis.evalsha(
                self._refill_batch_sha,
                1,  # Number of keys
                redis_key,
                self.REFILL_BATCH_SIZE
            )

            granted = int(granted)

            if granted > 0:
                # Successfully fetched, add to cache
                async with sku_cache.lock:
                    sku_cache.local_cache += granted
                    sku_cache.last_refill_time = time.time()

                logger.info(
                    f"[ASYNC] Refilled SKU {sku_id}: +{granted} items"
                )

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

    async def _proactive_refill_loop(self):
        """
        Proactive background refill loop (Gemini's recommendation).

        Continuously monitors all SKU buffers and refills them BEFORE they empty.
        This ensures the fast path (local RAM) is always available, avoiding
        the slow path (per-request Redis) that saturates Python's event loop.

        Key insight: At 10K RPS, we consume 100 items per millisecond.
        If refill takes 20ms, we need at least 2000 items buffer.
        With 70% watermark on 100K items, we have 70K items when refill triggers.
        This provides 700ms of buffer time - more than enough.
        """
        logger.info("Proactive refill loop started")

        while True:
            try:
                await asyncio.sleep(0.005)  # Check every 5ms

                for campaign_id, campaign in self._campaigns.items():
                    if campaign.status != "active":
                        continue

                    for sku_id, sku_cache in campaign.sku_caches.items():
                        # Check if refill needed (below 70% watermark)
                        if (
                            sku_cache.local_cache <= sku_cache.refill_watermark
                            and not sku_cache.refill_in_progress
                        ):
                            # Trigger immediate refill (don't wait for request)
                            asyncio.create_task(
                                self._async_refill_sku_from_redis(campaign_id, sku_id)
                            )

            except asyncio.CancelledError:
                logger.info("Proactive refill loop cancelled")
                break
            except Exception as e:
                logger.error(f"Proactive refill loop error: {e}")
                await asyncio.sleep(0.1)

    def start_proactive_refill(self):
        """Start the proactive refill background task"""
        if self._proactive_refill_task is None or self._proactive_refill_task.done():
            self._proactive_refill_task = asyncio.create_task(
                self._proactive_refill_loop()
            )
            logger.info("Proactive refill task started")

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
