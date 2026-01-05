"""
Service Startup: Claim and Load Campaign Allocations

This module handles initialization of Variant A adaptive inventory on service startup.

Lifecycle:
1. Service starts
2. Claim allocation units from DB
3. Load into AdaptiveInventoryManager (local memory)
4. Start serving requests (99%+ from RAM)
5. On shutdown: Release claims (optional)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.allocation_manager import AllocationManager
from app.services.adaptive_inventory_v2 import AdaptiveInventoryManager
import logging

logger = logging.getLogger(__name__)

# Global instances (singleton pattern)
_adaptive_manager: AdaptiveInventoryManager | None = None
_allocation_manager: AllocationManager | None = None


async def initialize_adaptive_inventory(
    db: AsyncSession,
    redis_client,
    campaign_id: str = "750e8400-e29b-41d4-a716-446655440000"
) -> tuple[AdaptiveInventoryManager, AllocationManager]:
    """
    Initialize adaptive inventory on service startup

    Args:
        db: Database session
        redis_client: Redis client
        campaign_id: Campaign to load allocations for

    Returns:
        (adaptive_manager, allocation_manager)
    """

    global _adaptive_manager, _allocation_manager

    logger.info("=" * 60)
    logger.info("VARIANT A: Initializing Adaptive Inventory System")
    logger.info("=" * 60)

    # Create managers
    _adaptive_manager = AdaptiveInventoryManager(redis_client)
    _allocation_manager = AllocationManager(_adaptive_manager)

    logger.info(f"Service ID: {_allocation_manager.service_id}")

    # Claim and load allocations
    claimed_count = await _allocation_manager.claim_and_load_allocations(
        db=db,
        campaign_id=campaign_id
    )

    if claimed_count == 0:
        logger.warning(
            "⚠️  No allocation units claimed! "
            "This service will fall back to Redis campaign pool immediately."
        )
    else:
        logger.info(f"✓ Successfully claimed and loaded {claimed_count} allocation units")

    # Get summary
    summary = await _allocation_manager.get_claimed_allocations_summary(db)
    logger.info(f"Allocation Summary: {summary}")

    # Get initial metrics
    metrics = _adaptive_manager.get_all_metrics()
    for metric in metrics:
        logger.info(
            f"  Unit {metric['allocation_id']}: "
            f"{metric['local_stock']} items in RAM, "
            f"low_water_mark={metric['current_low_water_mark']}"
        )

    logger.info("=" * 60)
    logger.info("✓ Adaptive Inventory Initialization Complete")
    logger.info("  Ready to serve requests from local memory!")
    logger.info("=" * 60)

    return _adaptive_manager, _allocation_manager


def get_adaptive_manager() -> AdaptiveInventoryManager:
    """Get the global adaptive inventory manager"""
    if _adaptive_manager is None:
        raise RuntimeError(
            "Adaptive inventory not initialized! "
            "Call initialize_adaptive_inventory() on startup."
        )
    return _adaptive_manager


def get_allocation_manager() -> AllocationManager:
    """Get the global allocation manager"""
    if _allocation_manager is None:
        raise RuntimeError(
            "Allocation manager not initialized! "
            "Call initialize_adaptive_inventory() on startup."
        )
    return _allocation_manager


async def shutdown_adaptive_inventory(db: AsyncSession):
    """
    Shutdown handler: Release claims and write back stranded stock

    Called on service shutdown (graceful)
    """

    global _allocation_manager

    if _allocation_manager is None:
        return

    logger.info("Shutting down adaptive inventory system...")

    try:
        # Release claims
        await _allocation_manager.release_claims(db)
        logger.info("✓ Released allocation claims")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("✓ Adaptive inventory shutdown complete")
