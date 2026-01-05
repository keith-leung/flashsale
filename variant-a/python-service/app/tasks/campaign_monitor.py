"""Background task to monitor flash sale campaigns and trigger write-back."""

import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.flash_sale_campaign import FlashSaleCampaign, FlashSaleStatus
from app.services.campaign_writeback import writeback_campaign

logger = logging.getLogger(__name__)

# Monitor interval (seconds)
MONITOR_INTERVAL = 60  # Check every 1 minute


async def campaign_monitor_task():
    """
    Background task that monitors flash sale campaigns.

    Triggers write-back when:
    - Campaign end_time has passed
    - Campaign status is still 'active'

    Runs every 60 seconds.
    """
    logger.info("Campaign monitor task started")

    while True:
        try:
            await _check_expired_campaigns()
        except Exception as e:
            logger.error(f"Error in campaign monitor task: {e}", exc_info=True)

        # Sleep for interval
        await asyncio.sleep(MONITOR_INTERVAL)


async def _check_expired_campaigns():
    """Check for expired campaigns and trigger write-back."""
    async with AsyncSessionLocal() as db:
        try:
            # Find campaigns that have expired but are still active
            now = datetime.utcnow()
            result = await db.execute(
                select(FlashSaleCampaign).filter(
                    FlashSaleCampaign.status == FlashSaleStatus.ACTIVE.value,
                    FlashSaleCampaign.end_time <= now
                )
            )
            expired_campaigns = result.scalars().all()

            if not expired_campaigns:
                logger.debug("No expired campaigns found")
                return

            logger.info(f"Found {len(expired_campaigns)} expired campaigns")

            # Trigger write-back for each expired campaign
            for campaign in expired_campaigns:
                logger.info(
                    f"Campaign {campaign.id} ({campaign.name}) expired at {campaign.end_time}, "
                    f"triggering write-back"
                )

                try:
                    # Trigger write-back
                    result = await writeback_campaign(
                        campaign_id=campaign.id,
                        db=db,
                        reason="scheduled_expiry"
                    )

                    logger.info(
                        f"Write-back completed for campaign {campaign.id}: "
                        f"{result.get('orders_written', 0)} orders"
                    )

                except Exception as e:
                    logger.error(
                        f"Error during write-back for campaign {campaign.id}: {e}",
                        exc_info=True
                    )
                    # Continue with other campaigns

        except Exception as e:
            logger.error(f"Error checking expired campaigns: {e}", exc_info=True)
