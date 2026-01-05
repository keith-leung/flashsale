"""
Allocation Manager - Claims and loads campaign allocations on service startup

Responsibilities:
1. Claim available allocation units from DB
2. Load them into AdaptiveInventoryManager (local memory)
3. Release claims on shutdown
"""

import os
import socket
from typing import List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.adaptive_inventory_v2 import AdaptiveInventoryManager
import logging

logger = logging.getLogger(__name__)


class AllocationManager:
    """
    Manages claiming and loading of campaign SKU allocations
    """

    def __init__(self, adaptive_manager: AdaptiveInventoryManager):
        self.adaptive_manager = adaptive_manager
        self.service_id = self._generate_service_id()
        self.claimed_allocation_ids: List[int] = []

    def _generate_service_id(self) -> str:
        """
        Generate unique service instance ID

        For benchmarking: Use simple format like 'python-1'
        For production: Could use pod name, hostname, etc.
        """
        hostname = socket.gethostname()
        pid = os.getpid()
        return f"python-{hostname}-{pid}"

    def _get_max_units_for_service(self) -> int:
        """
        Determine how many allocation units this service instance should claim

        For benchmarking: Hardcoded based on known capacity
        - C# service: 5 units (fastest)
        - Java service: 3 units (medium)
        - Python service: 2 units (slowest)

        For production: Could be dynamic based on:
        - Current load
        - /health benchmark results
        - Auto-scaling policies
        """

        # For benchmarking, use environment variable or default
        max_units = int(os.getenv('MAX_ALLOCATION_UNITS', '2'))

        logger.info(f"Service will attempt to claim {max_units} allocation units")
        return max_units

    async def claim_and_load_allocations(
        self,
        db: AsyncSession,
        campaign_id: str
    ) -> int:
        """
        Claim available allocation units and load into memory

        Returns:
            Number of units claimed
        """

        max_units = self._get_max_units_for_service()

        # Claim available units (with row lock to prevent double-claiming)
        claim_query = text("""
            UPDATE campaign_sku_allocations
            SET claimed_by = :service_id,
                claimed_at = NOW(),
                status = 'claimed'
            WHERE campaign_id = :campaign_id
              AND status = 'available'
            ORDER BY id
            LIMIT :max_units
        """)

        result = await db.execute(
            claim_query,
            {
                'service_id': self.service_id,
                'campaign_id': campaign_id,
                'max_units': max_units
            }
        )

        await db.commit()

        claimed_count = result.rowcount

        if claimed_count == 0:
            logger.warning(
                f"No allocation units available for campaign {campaign_id}. "
                f"All units may already be claimed by other service instances."
            )
            return 0

        logger.info(
            f"Claimed {claimed_count} allocation units for campaign {campaign_id}"
        )

        # Load claimed units into memory
        load_query = text("""
            SELECT
                id,
                campaign_id,
                sku_id,
                allocated_quantity,
                refill_batch_size,
                low_water_mark_pct
            FROM campaign_sku_allocations
            WHERE claimed_by = :service_id
              AND campaign_id = :campaign_id
        """)

        units_result = await db.execute(
            load_query,
            {
                'service_id': self.service_id,
                'campaign_id': campaign_id
            }
        )

        units = units_result.fetchall()

        for unit in units:
            self.adaptive_manager.add_unit(
                allocation_id=unit.id,
                campaign_id=unit.campaign_id,
                sku_id=unit.sku_id,
                allocated_quantity=unit.allocated_quantity,
                refill_batch_size=unit.refill_batch_size,
                low_water_mark_pct=float(unit.low_water_mark_pct)
            )

            self.claimed_allocation_ids.append(unit.id)

            logger.info(
                f"Loaded allocation unit {unit.id}: "
                f"SKU={unit.sku_id}, qty={unit.allocated_quantity}, "
                f"batch={unit.refill_batch_size}, watermark={unit.low_water_mark_pct}%"
            )

        total_allocated = sum(unit.allocated_quantity for unit in units)
        logger.info(
            f"Total inventory loaded: {total_allocated} items across {claimed_count} units"
        )

        return claimed_count

    async def release_claims(self, db: AsyncSession):
        """
        Release all claimed allocations (on service shutdown)

        Sets status back to 'available' so other instances can claim them
        """

        if not self.claimed_allocation_ids:
            return

        release_query = text("""
            UPDATE campaign_sku_allocations
            SET claimed_by = NULL,
                claimed_at = NULL,
                status = 'available'
            WHERE id IN :allocation_ids
              AND claimed_by = :service_id
        """)

        await db.execute(
            release_query,
            {
                'allocation_ids': tuple(self.claimed_allocation_ids),
                'service_id': self.service_id
            }
        )

        await db.commit()

        logger.info(
            f"Released {len(self.claimed_allocation_ids)} allocation units"
        )

        self.claimed_allocation_ids = []

    async def get_claimed_allocations_summary(self, db: AsyncSession) -> dict:
        """
        Get summary of claimed allocations for this service instance
        """

        query = text("""
            SELECT
                campaign_id,
                sku_id,
                COUNT(*) as unit_count,
                SUM(allocated_quantity) as total_quantity,
                AVG(refill_batch_size) as avg_batch_size
            FROM campaign_sku_allocations
            WHERE claimed_by = :service_id
            GROUP BY campaign_id, sku_id
        """)

        result = await db.execute(query, {'service_id': self.service_id})
        rows = result.fetchall()

        summary = []
        for row in rows:
            summary.append({
                'campaign_id': row.campaign_id,
                'sku_id': row.sku_id,
                'unit_count': row.unit_count,
                'total_quantity': row.total_quantity,
                'avg_batch_size': float(row.avg_batch_size)
            })

        return {
            'service_id': self.service_id,
            'allocations': summary
        }
