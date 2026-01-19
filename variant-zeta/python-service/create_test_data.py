import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.spu import SPU
from app.models.sku import SKU
from app.models.inventory import Inventory
from app.models.flash_sale import FlashSaleCampaign
from datetime import datetime, timedelta
import uuid

async def main():
    # Create async session
    engine = create_async_engine("mysql+aiomysql://syracuse:Orange_315_Forever!@mariadb:3306/orange315", future=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create SPU
        spu = SPU(
            id='e26bb7d0-c863-4cd6-b08c-44fcca0a8c28',
            name='iPhone 16 Pro',
            slug='iphone-16-pro',
            description='iPhone 16 Pro - Stress Test',
            is_active=True
        )
        session.add(spu)
        
        # Create SKU
        sku = SKU(
            id='2c2e23fa-f47b-4884-9b45-bf2a640f1ff3',
            spu_id=spu.id,
            name='iPhone 16 Pro 256GB',
            sku_code='IP16-256-BLK',
            price=999.99,
            is_active=True
        )
        session.add(sku)
        
        # Create inventory
        inventory = Inventory(
            id=str(uuid.uuid4()),
            sku_id=sku.id,
            quantity=10000,
            reserved_quantity=0
        )
        session.add(inventory)
        
        # Create campaign
        campaign = FlashSaleCampaign(
            id=str(uuid.uuid4()),
            name='iPhone 16 Pro Flash Sale',
            spu_id=spu.id,
            total_sale_limit=10000,
            sold_quantity=0,
            max_quantity_per_customer=1,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(hours=24),
            status='active',
            is_active=True
        )
        session.add(campaign)
        
        await session.commit()
        print(f"Created test data:")
        print(f"  SPU: {spu.id}")
        print(f"  SKU: {sku.id}")
        print(f"  Inventory: {inventory.quantity}")
        print(f"  Campaign: {campaign.id}")

if __name__ == "__main__":
    asyncio.run(main())
