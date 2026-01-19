"""Database initialization script for Variant Z."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

from app.core.database import Base, async_session_maker, DATABASE_URL
from app.models.spu import SPU
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.models.flash_sale import FlashSaleCampaign

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database tables and test data."""
    logger.info("Initializing database...")
    
    # Create all tables
    async with async_session_maker() as session:
        try:
            # Import all models to ensure they're registered with Base
            from app.models.spu import SPU
            from app.models.sku import SKU
            from app.models.inventory import Inventory
            from app.models.flash_sale import FlashSaleCampaign
            from app.models.order import Order
            from app.models.order_line_item import OrderLineItem
            from app.models.payment import Payment
            
            # Create tables
            async with async_session_maker().bind.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
            
            # Check if test data already exists
            result = await session.execute(select(SPU).where(SPU.slug == "test-flash-sale-product"))
            existing_spu = result.scalar_one_or_none()
            
            if existing_spu:
                logger.info("Test data already exists, skipping initialization")
                return
            
            # Create test SPU
            spu_id = str(uuid.uuid4())
            spu = SPU(
                id=spu_id,
                name="Flash Sale Test Product",
                slug="test-flash-sale-product",
                description="Test product for Variant Z flash sale",
                is_active=True
            )
            session.add(spu)
            await session.flush()
            logger.info(f"Created SPU: {spu.name}")
            
            # Create test SKU
            sku_id = str(uuid.uuid4())
            sku = SKU(
                id=sku_id,
                sku_code="FS-TEST-001",
                name="Flash Sale Test SKU",
                spu_id=spu_id,
                price=99.99,
                cost_price=50.00,
                is_active=True,
                track_inventory=True
            )
            session.add(sku)
            await session.flush()
            logger.info(f"Created SKU: {sku.sku_code}")
            
            # Create inventory
            inventory = Inventory(
                id=str(uuid.uuid4()),
                sku_id=sku_id,
                quantity=1000,
                reserved_quantity=0,
                allow_negative_stock=False
            )
            session.add(inventory)
            await session.flush()
            logger.info(f"Created inventory: {inventory.quantity} units")
            
            # Create flash sale campaign (active for next 24 hours)
            now = datetime.utcnow()
            campaign = FlashSaleCampaign(
                id=str(uuid.uuid4()),
                name="Test Flash Sale Campaign",
                description="Test campaign for Variant Z token pre-allocation",
                spu_id=spu_id,
                total_sale_limit=1000,
                sold_quantity=0,
                max_quantity_per_customer=1,
                start_time=now,
                end_time=now + timedelta(hours=24),
                status="active",
                is_active=True
            )
            session.add(campaign)
            await session.flush()
            logger.info(f"Created flash sale campaign: {campaign.name} (ID: {campaign.id})")
            
            # Commit all changes
            await session.commit()
            
            logger.info("=" * 60)
            logger.info("Database initialization completed successfully!")
            logger.info("=" * 60)
            logger.info(f"SPU ID: {spu_id}")
            logger.info(f"SKU ID: {sku_id}")
            logger.info(f"Campaign ID: {campaign.id}")
            logger.info(f"Inventory: {inventory.quantity} units")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            await session.rollback()
            raise


async def allocate_campaign_tokens():
    """Allocate tokens for active flash sale campaigns."""
    from app.core.token_manager import token_manager
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    
    logger.info("Allocating campaign tokens...")
    
    async with async_session_maker() as session:
        try:
            # Get active campaigns
            now = datetime.utcnow()
            result = await session.execute(
                select(FlashSaleCampaign)
                .where(FlashSaleCampaign.is_active == True)
                .where(FlashSaleCampaign.status == "active")
                .where(FlashSaleCampaign.start_time <= now)
                .where(FlashSaleCampaign.end_time >= now)
            )
            campaigns = result.scalars().all()
            
            if not campaigns:
                logger.info("No active campaigns found for token allocation")
                return
            
            for campaign in campaigns:
                try:
                    token_count = await token_manager.allocate_campaign_tokens(
                        db=session,
                        campaign_id=campaign.id,
                        spu_id=campaign.spu_id,
                        total_limit=campaign.total_sale_limit
                    )
                    logger.info(f"Allocated {token_count} tokens for campaign {campaign.id}")
                except Exception as e:
                    logger.error(f"Failed to allocate tokens for campaign {campaign.id}: {e}")
            
            logger.info("Token allocation completed")
            
        except Exception as e:
            logger.error(f"Error allocating campaign tokens: {e}")
            raise


async def main():
    """Main initialization function."""
    try:
        await init_database()
        await allocate_campaign_tokens()
        logger.info("Variant Z initialization completed successfully!")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())