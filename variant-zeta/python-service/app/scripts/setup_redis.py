"""Redis setup for Variant Zeta (Redis-First)."""

import asyncio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, text

DATABASE_URL = "mysql+aiomysql://syracuse:Orange_315_Forever!@localhost:3316/orange315"
REDIS_HOST = "localhost"
REDIS_PORT = 6379


async def setup_redis():
    """Load SKU and campaign data into Redis."""
    
    # Connect to databases
    engine = create_async_engine(DATABASE_URL, echo=False)
    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    print("Loading SKU and campaign data into Redis...")
    
    async with engine.begin() as conn:
        # Get all SKUs
        result = await conn.execute(
            text("SELECT id, sku_code, name, spu_id, price FROM skus WHERE is_active = TRUE")
        )
        skus = result.fetchall()
        
        print(f"Found {len(skus)} SKUs")
        
        for sku in skus:
            sku_id, sku_code, name, spu_id, price = sku
            
            # Load SKU metadata into Redis
            await redis.hset(f'sku:{sku_id}', mapping={
                'id': sku_id,
                'sku_code': sku_code,
                'name': name,
                'spu_id': spu_id,
                'price': str(price)
            })
            
            # Get inventory for this SKU
            inv_result = await conn.execute(
                text("SELECT quantity, reserved_quantity FROM inventory WHERE sku_id = %s"),
                (sku_id,)
            )
            inventory = inv_result.fetchone()
            
            if inventory:
                quantity, reserved = inventory
                
                # Load inventory into Redis
                await redis.hset(f'stock:{sku_id}', mapping={
                    'available': str(quantity),
                    'reserved': str(reserved)
                })
        
        print(f"✓ Loaded {len(skus)} SKUs into Redis")
        
        # Get all campaigns
        result = await conn.execute(
            text("SELECT id, spu_id, name, description, total_sale_limit, sold_quantity, start_time, end_time, flash_price, max_quantity_per_customer FROM flash_sale_campaigns WHERE is_active = TRUE AND status = 'active'")
        )
        campaigns = result.fetchall()
        
        print(f"Found {len(campaigns)} campaigns")
        
        for campaign in campaigns:
            (campaign_id, spu_id, name, description, total_limit, sold, 
             start_time, end_time, flash_price, max_qty) = campaign
            
            # Load campaign into Redis
            await redis.hset(f'campaign:{campaign_id}', mapping={
                'id': campaign_id,
                'spu_id': spu_id,
                'name': name,
                'description': description or '',
                'total_sale_limit': str(total_limit),
                'sold_quantity': str(sold),
                'start_time': str(start_time),
                'end_time': str(end_time),
                'flash_price': str(flash_price) if flash_price else '',
                'max_quantity_per_customer': str(max_qty)
            })
            
            # Index campaign by SPU
            await redis.set(f'campaign:spu:{spu_id}', campaign_id)
        
        print(f"✓ Loaded {len(campaigns)} campaigns into Redis")
    
    await redis.close()
    await engine.dispose()
    
    print("\n✓ Redis setup complete")


if __name__ == '__main__':
    asyncio.run(setup_redis())
