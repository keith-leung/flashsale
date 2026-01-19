"""Allocate tokens for all active campaigns in Variant Z."""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.token_manager import token_manager
from app.models.flash_sale import FlashSaleCampaign

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Allocate tokens for all active campaigns."""
    logger.info("Allocating tokens for all active campaigns...")
    
    async with async_session_maker() as db:
        try:
            # Get all active campaigns
            now = datetime.utcnow()
            result = await db.execute(
                select(FlashSaleCampaign)
                .where(FlashSaleCampaign.is_active == True)
                .where(FlashSaleCampaign.status == "active")
                .where(FlashSaleCampaign.start_time <= now)
                .where(FlashSaleCampaign.end_time >= now)
            )
            campaigns = result.scalars().all()
            
            if not campaigns:
                logger.warning("No active campaigns found")
                return
            
            logger.info(f"Found {len(campaigns)} active campaign(s)")
            
            for campaign in campaigns:
                try:
                    logger.info(f"\nProcessing campaign: {campaign.id}")
                    logger.info(f"  SPU ID: {campaign.spu_id}")
                    logger.info(f"  Total Limit: {campaign.total_sale_limit}")
                    logger.info(f"  Sold: {campaign.sold_quantity}")
                    
                    # Allocate tokens
                    token_count = await token_manager.allocate_campaign_tokens(
                        db=db,
                        campaign_id=campaign.id,
                        spu_id=campaign.spu_id,
                        total_limit=campaign.total_sale_limit
                    )
                    
                    logger.info(f"  ✓ Allocated {token_count} tokens")
                    
                except Exception as e:
                    logger.error(f"  ✗ Failed to allocate tokens: {e}")
            
            logger.info("\n" + "=" * 60)
            logger.info("Token allocation completed for all campaigns!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error allocating tokens: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())