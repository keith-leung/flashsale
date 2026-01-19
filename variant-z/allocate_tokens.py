#!/usr/bin/env python3
"""Allocate tokens for benchmark campaign."""
import asyncio
from app.core.token_manager import token_manager
from app.core.redis import redis_client

async def main():
    # Allocate tokens for campaign
    campaign_id = '67ca0e1e-0a59-473e-a04d-23fd26accd1b'
    sku_id = '5fe42b9b-6eb7-4fac-ac9b-a74a8209a2fc'
    
    # Allocate 9,999 tokens (campaign limit is 10,000, 1 already sold)
    result = await token_manager.allocate_campaign_tokens(
        campaign_id=campaign_id,
        sku_id=sku_id,
        total_tokens=9999
    )
    print(f'Token allocation result: {result}')
    
    # Cache SKU inventory
    await redis_client.set(f'sku:inventory:{sku_id}', 10000)
    print(f'Cached inventory for SKU {sku_id}: 10000')
    
    # Verify
    token_count = await redis_client.zcard(f'token:{campaign_id}')
    print(f'Tokens in Redis: {token_count}')

if __name__ == '__main__':
    asyncio.run(main())