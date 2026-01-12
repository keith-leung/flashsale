"""
Corrected Adaptive Inventory Service for Variant A
Producer-Consumer Pattern with Cascading Low Water Marks

Design:
- Local memory counter (pure RAM, no Redis on hot path)
- Async refill on low water mark (30% threshold)
- Cascading thresholds (150 → 45 → 13...)
- SpinWait panic buffer (brief wait if refill in progress)
- Semaphore coordination (single-flight refill)
"""

import asyncio
import time
from typing import Optional
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


class AdaptiveInventoryUnit:
    """
    Single allocation unit with producer-consumer pattern

    Consumer: Request threads decrement local_stock
    Producer: Async refill thread replenishes from Redis campaign pool
    """

    def __init__(
        self,
        allocation_id: int,
        campaign_id: str,
        sku_id: str,
        allocated_quantity: int,
        refill_batch_size: int,
        low_water_mark_pct: float,
        redis_client: redis.Redis
    ):
        self.allocation_id = allocation_id
        self.campaign_id = campaign_id
        self.sku_id = sku_id
        self.redis = redis_client

        # Configuration (from DB allocation table)
        self.initial_quantity = allocated_quantity
        self.refill_batch_size = refill_batch_size
        self.low_water_mark_pct = low_water_mark_pct / 100.0  # 30.00 → 0.30

        # Local memory counter (CONSUMER reads/writes)
        self._local_stock = allocated_quantity
        self._stock_lock = asyncio.Lock()

        # Refill coordination (PRODUCER)
        self._refill_semaphore = asyncio.Semaphore(1)  # Single-flight refill
        self._refill_in_progress = False
        self._current_low_water_mark = int(allocated_quantity * self.low_water_mark_pct)

        # Metrics
        self._total_requests = 0
        self._ram_hits = 0  # Served from local memory
        self._redis_refills = 0  # Times refilled from Redis
        self._redis_direct_hits = 0  # Fell back to Redis campaign pool

        # Redis keys
        # Refill from SKU-specific pool (Partitioned Layer 2)
        self._campaign_pool_key = f"fs:{campaign_id}:redis_pool:sku:{sku_id}"
        self._ordinary_stock_key = f"inv:{sku_id}"  # Ordinary stock fallback

        logger.info(
            f"[Allocation {allocation_id}] Initialized: {allocated_quantity} items, "
            f"refill_batch={refill_batch_size}, low_water_mark={self._current_low_water_mark}, "
            f"refill_source={self._campaign_pool_key}"
        )

    async def reserve_item(self) -> tuple[bool, str, float]:
        """
        Reserve one item using producer-consumer pattern

        Returns:
            (success, price_type, price_value)
            price_type: 'campaign', 'ordinary', or 'sold_out'
        """
        self._total_requests += 1

        # Fast path: Try local memory (CONSUMER - pure RAM)
        async with self._stock_lock:
            if self._local_stock > 0:
                self._local_stock -= 1
                self._ram_hits += 1

                # Check if hit low water mark (trigger async refill)
                if self._local_stock == self._current_low_water_mark and not self._refill_in_progress:
                    # Trigger async refill (non-blocking)
                    asyncio.create_task(self._async_refill())

                return (True, 'campaign', 79.99)

        # Slow path: Local depleted, try panic buffer
        return await self._handle_depleted()

    async def _handle_depleted(self) -> tuple[bool, str, float]:
        """
        Handle local stock depletion

        Flow:
        1. If refill in progress, SpinWait briefly (panic buffer)
        2. Try Redis campaign pool (dual stock)
        3. Fall back to ordinary stock
        """

        # Panic Buffer: If refill in progress, wait briefly for it to complete
        if self._refill_in_progress:
            logger.debug(f"[Allocation {self.allocation_id}] Panic buffer: refill in progress, waiting...")

            # SpinWait up to 10ms for refill to complete
            start = time.perf_counter()
            max_wait_ms = 10

            while (time.perf_counter() - start) * 1000 < max_wait_ms:
                async with self._stock_lock:
                    if self._local_stock > 0:
                        # Refill completed! Take from newly refilled stock
                        self._local_stock -= 1
                        self._ram_hits += 1
                        logger.debug(f"[Allocation {self.allocation_id}] Panic buffer SUCCESS: got item from refill")
                        return (True, 'campaign', 79.99)

                await asyncio.sleep(0.001)  # 1ms spin

            logger.debug(f"[Allocation {self.allocation_id}] Panic buffer timeout, falling back to Redis")

        # Try Redis campaign pool (DUAL STOCK - still campaign price)
        campaign_remaining = await self.redis.decr(self._campaign_pool_key)

        if campaign_remaining >= 0:
            self._redis_direct_hits += 1
            logger.info(
                f"[Allocation {self.allocation_id}] Redis campaign pool hit, "
                f"remaining: {campaign_remaining}"
            )
            return (True, 'campaign', 79.99)
        else:
            # Campaign sold out, rollback the decrement
            await self.redis.incr(self._campaign_pool_key)

        # Fall back to ordinary stock (BENCHMARK SHOULD STOP HERE)
        ordinary_remaining = await self.redis.decr(self._ordinary_stock_key)

        if ordinary_remaining >= 0:
            logger.warning(
                f"[Allocation {self.allocation_id}] Fell back to ordinary stock! "
                f"Campaign sold out. Ordinary remaining: {ordinary_remaining}"
            )
            return (True, 'ordinary', 99.99)
        else:
            # Completely sold out
            await self.redis.incr(self._ordinary_stock_key)
            return (False, 'sold_out', 0.0)

    async def _async_refill(self):
        """
        PRODUCER: Async refill from Redis campaign pool

        Uses semaphore to prevent concurrent refills (single-flight pattern)
        Implements cascading low water marks
        """

        # Try to acquire semaphore (non-blocking check)
        if not self._refill_semaphore.locked():
            async with self._refill_semaphore:
                await self._do_refill()
        else:
            logger.debug(f"[Allocation {self.allocation_id}] Refill already in progress, skipping")

    async def _do_refill(self):
        """Execute the actual refill operation"""

        self._refill_in_progress = True
        refill_start = time.perf_counter()

        try:
            # Calculate refill amount
            refill_amount = self.refill_batch_size

            # Check if refill amount too small (not worth overhead)
            current_stock = self._local_stock
            if current_stock < 10 and refill_amount < 10:
                logger.info(
                    f"[Allocation {self.allocation_id}] Skipping refill: "
                    f"stock={current_stock}, refill={refill_amount} too small"
                )
                return

            # DECRBY Redis campaign pool (ONLY HERE - rare Redis call!)
            campaign_remaining = await self.redis.decrby(self._campaign_pool_key, refill_amount)

            if campaign_remaining >= 0:
                # Success: Add to local stock
                async with self._stock_lock:
                    old_stock = self._local_stock
                    self._local_stock += refill_amount

                    # Update cascading low water mark (30% of new stock)
                    self._current_low_water_mark = int(self._local_stock * self.low_water_mark_pct)

                    self._redis_refills += 1

                    refill_latency_ms = (time.perf_counter() - refill_start) * 1000

                    logger.info(
                        f"[Allocation {self.allocation_id}] Refill SUCCESS: "
                        f"{old_stock} → {self._local_stock} (+{refill_amount}), "
                        f"new_low_mark={self._current_low_water_mark}, "
                        f"campaign_pool={campaign_remaining}, "
                        f"latency={refill_latency_ms:.2f}ms"
                    )
            else:
                # Campaign pool depleted, rollback
                await self.redis.incrby(self._campaign_pool_key, refill_amount)
                logger.warning(
                    f"[Allocation {self.allocation_id}] Refill FAILED: "
                    f"campaign pool depleted"
                )

        except Exception as e:
            logger.error(f"[Allocation {self.allocation_id}] Refill error: {e}")

        finally:
            self._refill_in_progress = False

    def get_metrics(self) -> dict:
        """Get performance metrics"""
        return {
            'allocation_id': self.allocation_id,
            'local_stock': self._local_stock,
            'current_low_water_mark': self._current_low_water_mark,
            'total_requests': self._total_requests,
            'ram_hits': self._ram_hits,
            'redis_refills': self._redis_refills,
            'redis_direct_hits': self._redis_direct_hits,
            'ram_hit_rate': f"{(self._ram_hits / self._total_requests * 100) if self._total_requests > 0 else 0:.2f}%"
        }

    async def get_stranded_stock(self) -> int:
        """Get remaining local stock (for write-back on campaign end)"""
        async with self._stock_lock:
            return self._local_stock

    async def clear_stock(self):
        """Clear local stock (after write-back)"""
        async with self._stock_lock:
            self._local_stock = 0


class AdaptiveInventoryManager:
    """
    Manages multiple allocation units for a campaign/SKU
    Each service instance may claim multiple units
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._units: dict[int, AdaptiveInventoryUnit] = {}  # allocation_id → unit
        self._sku_units: dict[str, list[AdaptiveInventoryUnit]] = {}  # sku_id → [units]
        self._round_robin_index: dict[str, int] = {}  # sku_id → current index

    def add_unit(
        self,
        allocation_id: int,
        campaign_id: str,
        sku_id: str,
        allocated_quantity: int,
        refill_batch_size: int,
        low_water_mark_pct: float
    ):
        """Add an allocation unit to be managed"""

        unit = AdaptiveInventoryUnit(
            allocation_id=allocation_id,
            campaign_id=campaign_id,
            sku_id=sku_id,
            allocated_quantity=allocated_quantity,
            refill_batch_size=refill_batch_size,
            low_water_mark_pct=low_water_mark_pct,
            redis_client=self.redis
        )

        self._units[allocation_id] = unit

        if sku_id not in self._sku_units:
            self._sku_units[sku_id] = []
            self._round_robin_index[sku_id] = 0

        self._sku_units[sku_id].append(unit)

        logger.info(f"Added allocation unit {allocation_id} for SKU {sku_id}")

    async def reserve_item(self, sku_id: str) -> tuple[bool, str, float]:
        """
        Reserve item from any available unit for this SKU
        Uses round-robin across units for load balancing
        """

        if sku_id not in self._sku_units or not self._sku_units[sku_id]:
            # No local units - fall back to Redis directly
            logger.info(f"No allocation units for SKU {sku_id}, falling back to Redis campaign pool")
            return await self._fallback_to_redis(sku_id)

        units = self._sku_units[sku_id]
        start_index = self._round_robin_index[sku_id]

        # Try each unit in round-robin order
        for i in range(len(units)):
            index = (start_index + i) % len(units)
            unit = units[index]

            success, price_type, price = await unit.reserve_item()

            if success and price_type == 'campaign':
                # Update round-robin for next request
                self._round_robin_index[sku_id] = (index + 1) % len(units)
                return (success, price_type, price)

        # All units depleted, try first unit's fallback logic (Redis campaign pool + ordinary)
        return await units[0]._handle_depleted()

    async def _fallback_to_redis(self, sku_id: str) -> tuple[bool, str, float]:
        """
        Fallback to Redis when no local units available
        Tries: campaign pool → ordinary stock
        """
        # Assume campaign_id and keys (would need to be passed or configured)
        campaign_pool_key = f"fs:750e8400-e29b-41d4-a716-446655440000:limit"
        ordinary_stock_key = f"inv:{sku_id}"

        # Try Redis campaign pool
        campaign_remaining = await self.redis.decr(campaign_pool_key)
        if campaign_remaining >= 0:
            logger.info(f"Redis campaign pool hit for SKU {sku_id}, remaining: {campaign_remaining}")
            return (True, 'campaign', 79.99)
        else:
            # Rollback
            await self.redis.incr(campaign_pool_key)

        # Fall back to ordinary stock
        ordinary_remaining = await self.redis.decr(ordinary_stock_key)
        if ordinary_remaining >= 0:
            logger.warning(f"Fell back to ordinary stock for SKU {sku_id}, remaining: {ordinary_remaining}")
            return (True, 'ordinary', 99.99)
        else:
            # Completely sold out
            await self.redis.incr(ordinary_stock_key)
            return (False, 'sold_out', 0.0)

    def get_all_metrics(self) -> list[dict]:
        """Get metrics from all units"""
        return [unit.get_metrics() for unit in self._units.values()]

    async def get_total_stranded_stock(self, sku_id: str) -> int:
        """Get total stranded stock across all units for a SKU"""
        if sku_id not in self._sku_units:
            return 0

        total = 0
        for unit in self._sku_units[sku_id]:
            total += await unit.get_stranded_stock()

        return total

    async def clear_all_stock(self, sku_id: str):
        """Clear all stock for a SKU (after write-back)"""
        if sku_id in self._sku_units:
            for unit in self._sku_units[sku_id]:
                await unit.clear_stock()
