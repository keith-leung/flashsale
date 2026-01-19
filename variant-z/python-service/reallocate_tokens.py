"""Re-allocate campaign tokens for benchmark testing."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.token_manager import token_manager
from app.models.flash_sale import FlashSaleCampaign
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Re-allocate tokens for the benchmark campaign."""
    # Database connection
    engine = create_async_engine(
        "mysql+aiomysql://syracuse:Orange_315_Forever!@flash-mariadb-z:3306/orange315",
        echo=False
    )
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        # Get the benchmark campaign
        result = await db.execute(
            select(FlashSaleCampaign)
            .where(FlashSaleCampaign.id == "e26bb7d0-c863-4cd6-b08c-44fcca0a8c28")
        )
        campaign = result.scalar_one_or_none()
        
        if not campaign:
            logger.error("Campaign not found!")
            return
        
        logger.info(f"Found campaign: {campaign.id}")
        logger.info(f"SPU ID: {campaign.spu_id}")
        logger.info(f"Total Sale Limit: {campaign.total_sale_limit}")
        
        # Allocate tokens
        tokens_allocated = await token_manager.allocate_campaign_tokens(
            db=db,
            campaign_id=campaign.id,
            spu_id=campaign.spu_id,
            total_limit=campaign.total_sale_limit
        )
        
        logger.info(f"Allocated {tokens_allocated} tokens")
    
    await engine.dispose()
    logger.info("Token allocation completed!")


if __name__ == "__main__":
    asyncio.run(main())