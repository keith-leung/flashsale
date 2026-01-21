"""Redis client for Variant U - Distributed Token Reserve."""
import redis.asyncio as redis
import logging
import time
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client with connection pooling and Lua script management."""
    
    def __init__(self, host: str = "10.91.0.3", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.pool: Optional[redis.ConnectionPool] = None
        self.client: Optional[redis.Redis] = None
        self._order_validation_script: Optional[redis.Script] = None
        
    async def connect(self):
        """Establish Redis connection pool."""
        self.pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            max_connections=50,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.pool)
        
        # Load Lua scripts
        await self._load_lua_scripts()
        logger.info(f"Redis connected to {self.host}:{self.port}/{self.db}")
        
    async def _load_lua_scripts(self):
        """Load Lua scripts for atomic operations."""
        # Lua script for atomic order validation and token reservation
        order_validation_script = """
        -- KEYS[1]: campaign:limit:{campaign_id}
        -- KEYS[2]: sku:inventory:{sku_id}
        -- ARGV[1]: order_id
        -- ARGV[2]: quantity (always 1 for flash sale)
        -- ARGV[3]: timestamp
        
        local campaign_limit_key = KEYS[1]
        local sku_inventory_key = KEYS[2]
        local order_id = ARGV[1]
        local quantity = tonumber(ARGV[2])
        local timestamp = ARGV[3]
        
        -- Check campaign limit
        local campaign_remaining = tonumber(redis.call('GET', campaign_limit_key))
        if campaign_remaining == nil then
            return {0, "campaign_not_found"}
        end
        
        if campaign_remaining < quantity then
            return {0, "campaign_sold_out"}
        end
        
        -- Check SKU inventory
        local sku_inventory = tonumber(redis.call('GET', sku_inventory_key))
        if sku_inventory == nil then
            return {0, "sku_not_found"}
        end
        
        if sku_inventory < quantity then
            return {0, "sku_out_of_stock"}
        end
        
        -- Atomically decrement both counters
        redis.call('DECRBY', campaign_limit_key, quantity)
        redis.call('DECRBY', sku_inventory_key, quantity)
        
        -- Add to order stream for async persistence
        local stream_key = "orders:stream"
        local order_data = {
            order_id = order_id,
            sku_id = string.match(sku_inventory_key, "sku:inventory:(.+)"),
            campaign_id = string.match(campaign_limit_key, "campaign:limit:(.+)"),
            quantity = quantity,
            timestamp = timestamp,
            status = "reserved"
        }
        
        redis.call('XADD', stream_key, '*', 'data', cjson.encode(order_data))
        
        -- Return success with remaining counts
        local new_campaign_remaining = tonumber(redis.call('GET', campaign_limit_key))
        local new_sku_inventory = tonumber(redis.call('GET', sku_inventory_key))
        
        return {1, order_id, new_campaign_remaining, new_sku_inventory}
        """
        
        self._order_validation_script = self.client.register_script(order_validation_script)
        
    async def validate_and_reserve_order(
        self, 
        campaign_id: str,
        sku_id: str,
        order_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Validate campaign limit and SKU inventory, then reserve tokens.
        
        Returns: {
            "success": bool,
            "order_id": str or None,
            "error": str or None,
            "campaign_remaining": int or None,
            "sku_remaining": int or None
        }
        """
        try:
            result = await self._order_validation_script(
                keys=[f"campaign:limit:{campaign_id}", f"sku:inventory:{sku_id}"],
                args=[order_id, str(quantity), str(int(time.time()))]
            )
            
            if result[0] == 1:  # Success
                return {
                    "success": True,
                    "order_id": result[1],
                    "campaign_remaining": result[2],
                    "sku_remaining": result[3],
                    "error": None
                }
            else:  # Failure
                return {
                    "success": False,
                    "order_id": None,
                    "error": result[1],
                    "campaign_remaining": None,
                    "sku_remaining": None
                }
                
        except Exception as e:
            logger.error(f"Redis validation failed: {e}")
            return {
                "success": False,
                "order_id": None,
                "error": f"redis_error: {str(e)}",
                "campaign_remaining": None,
                "sku_remaining": None
            }
    
    async def initialize_campaign(self, campaign_id: str, total_limit: int):
        """Initialize campaign tokens in Redis."""
        await self.client.set(f"campaign:limit:{campaign_id}", total_limit)
        
    async def initialize_sku_inventory(self, sku_id: str, quantity: int):
        """Initialize SKU inventory in Redis."""
        await self.client.set(f"sku:inventory:{sku_id}", quantity)
    
    async def get_campaign_remaining(self, campaign_id: str) -> Optional[int]:
        """Get remaining campaign tokens."""
        result = await self.client.get(f"campaign:limit:{campaign_id}")
        return int(result) if result else None
        
    async def get_sku_inventory(self, sku_id: str) -> Optional[int]:
        """Get SKU inventory."""
        result = await self.client.get(f"sku:inventory:{sku_id}")
        return int(result) if result else None
        
    async def close(self):
        """Close Redis connections."""
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

# Global Redis client instance
redis_client = RedisClient()