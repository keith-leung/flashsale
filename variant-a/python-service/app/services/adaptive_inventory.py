"""
Adaptive Inventory Service for Flash Sale Variant A

Uses a 2-tier adaptive strategy:
- BATCH MODE: Local cache with asyncio.Lock (500 items)
- DIRECT MODE: Direct Redis calls when stock < LOW_WATER_MARK

Network I/O Reduction: 99.6%+ (500 requests = 1 Redis call in batch mode)
"""

import asyncio
import sys
from typing import Tuple, Optional
import redis.asyncio as redis


class AdaptiveInventoryService:
    """Adaptive inventory service for a specific campaign/SKU combination"""

    # Configuration
    BATCH_SIZE = 500
    LOW_WATER_MARK = 2000

    def __init__(self, campaign_id: str, sku_id: str, redis_client: redis.Redis, lua_script_sha: str):
        """
        Initialize the adaptive inventory service for a specific SKU

        Args:
            campaign_id: Flash sale campaign ID
            sku_id: SKU ID
            redis_client: Shared async Redis client
            lua_script_sha: Pre-loaded Lua script SHA
        """
        self.campaign_id = campaign_id
        self.sku_id = sku_id
        self._redis = redis_client
        self._lua_script_sha = lua_script_sha

        # Redis key for this SKU's inventory (matches init_redis_pools.py format)
        self._inventory_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"

        # L1 Cache (Local Memory)
        self._local_stock = 0
        self._stock_lock = asyncio.Lock()

        # Mode control
        self._direct_mode = False

        # Single-flight refill protection
        self._refill_lock = asyncio.Lock()

        # Metrics
        self._batch_mode_requests = 0
        self._direct_mode_requests = 0
        self._total_redis_calls = 0
        self._mode_switched = False

    async def reserve_item(self) -> bool:
        """
        Attempt to reserve one item from inventory

        Hot Path Flow:
        1. Try local cache (pure memory, no network)
        2. If cache empty, refill from Redis (single-flight)
        3. If directMode, bypass cache and hit Redis

        Returns:
            True if reservation successful, False if sold out
        """
        # Fast path: Try local cache first (BATCH MODE)
        if not self._direct_mode:
            async with self._stock_lock:
                if self._local_stock > 0:
                    self._local_stock -= 1
                    self._batch_mode_requests += 1
                    return True  # ← Network I/O saved here! Pure RAM operation

        # Slow path: Refill or direct Redis
        return await self._refill_or_direct()

    async def _refill_or_direct(self) -> bool:
        """
        Refill local cache from Redis or switch to direct mode
        Uses single-flight pattern to prevent stampede
        """
        async with self._refill_lock:
            # Double-check: another coroutine might have refilled
            if not self._direct_mode:
                async with self._stock_lock:
                    if self._local_stock > 0:
                        self._local_stock -= 1
                        self._batch_mode_requests += 1
                        return True

            if self._direct_mode:
                # Direct mode: hit Redis for every request
                return await self._try_direct_redis()
            else:
                # Batch mode: try to refill from Redis
                return await self._try_refill_batch()

    async def _try_refill_batch(self) -> bool:
        """Try to refill local cache from Redis using Lua script"""
        self._total_redis_calls += 1

        # Call Lua script
        result = await self._redis.evalsha(
            self._lua_script_sha,
            1,  # Number of keys
            self._inventory_key,
            self.BATCH_SIZE,
            self.LOW_WATER_MARK
        )

        granted = int(result)

        if granted == -1:
            # Sold out
            return False
        elif granted == -2:
            # Switch to direct mode
            if not self._mode_switched:
                self._mode_switched = True
                print(f"[MODE SWITCH] SKU {self.sku_id}: Stock below {self.LOW_WATER_MARK} - "
                      f"switching to DIRECT mode to prevent fragmentation", file=sys.stderr)
            self._direct_mode = True
            return await self._try_direct_redis()
        else:
            # Granted batch
            async with self._stock_lock:
                self._local_stock = granted
                if self._local_stock > 0:
                    self._local_stock -= 1
                    self._batch_mode_requests += 1
                    return True
            return False

    async def _try_direct_redis(self) -> bool:
        """
        Direct Redis mode - hit Redis for every request
        Used when stock < LOW_WATER_MARK to prevent fragmentation
        """
        self._total_redis_calls += 1
        self._direct_mode_requests += 1

        # Atomic decrement
        stock = await self._redis.decr(self._inventory_key)
        if stock >= 0:
            return True
        else:
            # Restore if went negative
            await self._redis.incr(self._inventory_key)
            return False

    def get_metrics(self) -> Tuple[int, int, int, bool]:
        """
        Get current metrics

        Returns:
            (batch_mode_requests, direct_mode_requests, total_redis_calls, mode_switched)
        """
        return (
            self._batch_mode_requests,
            self._direct_mode_requests,
            self._total_redis_calls,
            self._mode_switched
        )

    @property
    def current_mode(self) -> str:
        """Get current operation mode"""
        return "DIRECT" if self._direct_mode else "BATCH"


class AdaptiveInventoryManager:
    """
    Manages adaptive inventory services for multiple SKUs
    Singleton pattern - one instance per campaign
    """

    def __init__(self, redis_client: redis.Redis):
        """Initialize with shared Redis client"""
        self._redis = redis_client
        self._lua_script_sha: Optional[str] = None
        self._services: dict[str, AdaptiveInventoryService] = {}
        self._init_lock = asyncio.Lock()

    async def initialize(self, lua_script_path: str = "/app/app/lua/inventory_refill.lua"):
        """Load Lua script into Redis"""
        if self._lua_script_sha is None:
            async with self._init_lock:
                if self._lua_script_sha is None:
                    with open(lua_script_path, "r") as f:
                        lua_script = f.read()
                    self._lua_script_sha = await self._redis.script_load(lua_script)
                    print(f"AdaptiveInventoryManager initialized", file=sys.stderr)
                    print(f"  Lua Script SHA: {self._lua_script_sha}", file=sys.stderr)

    async def get_service(self, campaign_id: str, sku_id: str) -> AdaptiveInventoryService:
        """
        Get or create adaptive inventory service for a SKU

        Args:
            campaign_id: Campaign ID
            sku_id: SKU ID

        Returns:
            AdaptiveInventoryService instance for this SKU
        """
        if self._lua_script_sha is None:
            await self.initialize()

        service_key = f"{campaign_id}:{sku_id}"

        if service_key not in self._services:
            self._services[service_key] = AdaptiveInventoryService(
                campaign_id=campaign_id,
                sku_id=sku_id,
                redis_client=self._redis,
                lua_script_sha=self._lua_script_sha
            )

        return self._services[service_key]

    def get_all_metrics(self) -> dict:
        """Get metrics for all active services"""
        metrics = {}
        for key, service in self._services.items():
            batch, direct, redis_calls, switched = service.get_metrics()
            metrics[key] = {
                "batch_mode_requests": batch,
                "direct_mode_requests": direct,
                "total_redis_calls": redis_calls,
                "mode_switched": switched,
                "current_mode": service.current_mode
            }
        return metrics
