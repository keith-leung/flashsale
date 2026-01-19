"""Setup flash sale campaigns with cache pre-loading (BUG-FREE)."""

import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, Base
from app.models.flash_sale import FlashSaleCampaign
from app.core.campaign_cache import campaign_cache_service


async def main():
    """Setup flash sale campaigns and pre-load to Redis."""
    print("Setting up flash sale campaigns...")
    
    # Create campaign
    campaign_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    campaign_data = {
        'id': campaign_id,
        'name': 'iPhone 16 Pro Flash Sale',
        'spu_id': 'e26bb7d0-c863-4cd6-b08c-44fcca0a8c28',  # From test data
        'total_sale_limit': 10000,
        'sold_quantity': 0,
        'max_quantity_per_customer': 1,
        'start_time': now,
        'end_time': now + timedelta(hours=24),
        'status': 'active',
        'is_active': True
    }
    
    async with AsyncSessionLocal() as db:
        # Check if campaign already exists
        result = await db.execute(
            select(FlashSaleCampaign)
            .where(FlashSaleCampaign.spu_id == campaign_data['spu_id'])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Campaign already exists for SPU {campaign_data['spu_id']}")
            campaign = existing
        else:
            # Create campaign
            campaign = FlashSaleCampaign(**campaign_data)
            db.add(campaign)
            await db.commit()
            await db.refresh(campaign)
            print(f"Created campaign {campaign_id} for SPU {campaign_data['spu_id']}")
        
        # Pre-load to Redis
        await campaign_cache_service.pre_load_campaign(db, campaign)
        print(f"Pre-loaded campaign {campaign.id} (SPU: {campaign.spu_id}) to Redis")
    
    print("Flash sale campaigns setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
