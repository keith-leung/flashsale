"""Test data setup script for Variant Z."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.token_manager import token_manager
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


async def create_test_flash_sale():
    """Create a test flash sale campaign with SPU, SKU, and inventory."""
    logger.info("Creating test flash sale data...")
    
    async with async_session_maker() as session:
        try:
            # Create test SPU
            spu_id = str(uuid.uuid4())
            spu = SPU(
                id=spu_id,
                name="Flash Sale Product - Test",
                slug="flash-sale-test-product",
                description="Test product for Variant Z flash sale benchmarking",
                is_active=True
            )
            session.add(spu)
            await session.flush()
            logger.info(f"✓ Created SPU: {spu.name} (ID: {spu_id})")
            
            # Create test SKU
            sku_id = str(uuid.uuid4())
            sku = SKU(
                id=sku_id,
                sku_code="FS-TEST-BENCHMARK-001",
                name="Flash Sale Benchmark SKU",
                spu_id=spu_id,
                price=99.99,
                cost_price=50.00,
                is_active=True,
                track_inventory=True
            )
            session.add(sku)
            await session.flush()
            logger.info(f"✓ Created SKU: {sku.sku_code} (ID: {sku_id})")
            
            # Create inventory
            inventory = Inventory(
                id=str(uuid.uuid4()),
                sku_id=sku_id,
                quantity=10000,
                reserved_quantity=0,
                allow_negative_stock=False
            )
            session.add(inventory)
            await session.flush()
            logger.info(f"✓ Created inventory: {inventory.quantity} units")
            
            # Create flash sale campaign (active for next 24 hours)
            now = datetime.utcnow()
            campaign = FlashSaleCampaign(
                id=str(uuid.uuid4()),
                name="Benchmark Flash Sale Campaign",
                description="Benchmark campaign for Variant Z token pre-allocation",
                spu_id=spu_id,
                total_sale_limit=10000,
                sold_quantity=0,
                max_quantity_per_customer=1,
                start_time=now,
                end_time=now + timedelta(hours=24),
                status="active",
                is_active=True
            )
            session.add(campaign)
            await session.flush()
            logger.info(f"✓ Created flash sale campaign: {campaign.name} (ID: {campaign.id})")
            
            # Commit changes
            await session.commit()
            
            # Allocate tokens for the campaign
            logger.info(f"Allocating {campaign.total_sale_limit} tokens for campaign {campaign.id}...")
            token_count = await token_manager.allocate_campaign_tokens(
                db=session,
                campaign_id=campaign.id,
                spu_id=spu_id,
                total_limit=campaign.total_sale_limit
            )
            logger.info(f"✓ Allocated {token_count} tokens")
            
            # Print summary
            logger.info("=" * 70)
            logger.info("TEST FLASH SALE DATA CREATED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"SPU ID:      {spu_id}")
            logger.info(f"SKU ID:      {sku_id}")
            logger.info(f"SKU Code:    {sku.sku_code}")
            logger.info(f"Price:       ${sku.price}")
            logger.info(f"Campaign ID: {campaign.id}")
            logger.info(f"Tokens:      {token_count}")
            logger.info(f"Inventory:   {inventory.quantity} units")
            logger.info("=" * 70)
            logger.info("\nUse this data for benchmarking:")
            logger.info(f'curl -X POST http://localhost:30017/api/v1/orders \\')
            logger.info(f'  -H "Content-Type: application/json" \\')
            logger.info(f'  -d \'{{')
            logger.info(f'    "customer_name": "Test Customer",')
            logger.info(f'    "customer_email": "test@example.com",')
            logger.info(f'    "line_items": [{{"sku_id": "{sku_id}", "quantity": 1}}]')
            logger.info(f'  }}\'')
            logger.info("=" * 70)
            
            # Write SKU ID to file for wrk benchmark script
            with open('/tmp/stress_test_sku_ids.txt', 'w') as f:
                f.write(f"{sku_id}\n")
            logger.info(f"✓ SKU ID written to /tmp/stress_test_sku_ids.txt")

            return {
                "spu_id": spu_id,
                "sku_id": sku_id,
                "sku_code": sku.sku_code,
                "campaign_id": campaign.id,
                "tokens": token_count,
                "price": float(sku.price)
            }
            
        except Exception as e:
            logger.error(f"Error creating test data: {e}")
            await session.rollback()
            raise


async def check_existing_data():
    """Check if test data already exists."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(SPU).where(SPU.slug == "flash-sale-test-product")
        )
        spu = result.scalar_one_or_none()
        
        if spu:
            logger.info("Test data already exists")
            
            # Get SKU
            sku_result = await session.execute(
                select(SKU).where(SKU.spu_id == spu.id)
            )
            sku = sku_result.scalar_one_or_none()
            
            if sku:
                # Get inventory
                inv_result = await session.execute(
                    select(Inventory).where(Inventory.sku_id == sku.id)
                )
                inventory = inv_result.scalar_one_or_none()
                
                # Get campaign
                camp_result = await session.execute(
                    select(FlashSaleCampaign)
                    .where(FlashSaleCampaign.spu_id == spu.id)
                    .where(FlashSaleCampaign.status == "active")
                )
                campaign = camp_result.scalar_one_or_none()
                
                logger.info("=" * 70)
                logger.info("EXISTING TEST DATA")
                logger.info("=" * 70)
                logger.info(f"SPU ID:      {spu.id}")
                logger.info(f"SKU ID:      {sku.id}")
                logger.info(f"SKU Code:    {sku.sku_code}")
                logger.info(f"Price:       ${sku.price}")
                if campaign:
                    logger.info(f"Campaign ID: {campaign.id}")
                    tokens = await token_manager.get_campaign_remaining_tokens(campaign.id)
                    logger.info(f"Tokens:      {tokens}")
                if inventory:
                    logger.info(f"Inventory:   {inventory.quantity} units")
                logger.info("=" * 70)

                # Write SKU ID to file for wrk benchmark script
                with open('/tmp/stress_test_sku_ids.txt', 'w') as f:
                    f.write(f"{sku.id}\n")
                logger.info(f"✓ SKU ID written to /tmp/stress_test_sku_ids.txt")

                return True
        
        return False


async def main():
    """Main setup function."""
    try:
        # Check if data already exists
        exists = await check_existing_data()
        
        if not exists:
            # Create new test data
            await create_test_flash_sale()
        else:
            logger.info("Skipping test data creation (already exists)")
        
        logger.info("Test data setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())