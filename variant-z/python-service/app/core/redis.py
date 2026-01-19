"""Redis client for token pre-allocation (Variant Z)."""

import logging
import os
from typing import Optional, Any

from redis.asyncio import Redis as AsyncRedis, ConnectionPool
from redis import RedisError

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with connection pooling for Variant Z."""
    
    def __init__(self):
        """Initialize Redis client from environment variables."""
        self.host = os.getenv("REDIS_HOST", "redis")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.client: Optional[AsyncRedis] = None
        self.pool: Optional[ConnectionPool] = None
        # Cache Lua scripts to avoid repeated file I/O
        self._lua_script_cache: dict[str, str] = {}
        
    async def connect(self):
        """Establish Redis connection with connection pooling."""
        if self.client is None:
            try:
                # Create connection pool (optimized for high concurrency)
                self.pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    max_connections=100,  # Increased from 50
                )
                
                # Create Redis client from pool
                self.client = AsyncRedis(connection_pool=self.pool)
                
                # Test connection
                await self.client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
    
    async def disconnect(self):
        """Close Redis connection and pool."""
        if self.client:
            await self.client.aclose()
            self.client = None
        if self.pool:
            await self.pool.aclose()
            self.pool = None
        logger.info("Disconnected from Redis")
    
    async def _ensure_connected(self):
        """Ensure Redis client is connected."""
        if self.client is None or self.pool is None:
            await self.connect()
    
    async def execute_lua_script(self, script_path: str, keys: list[str], args: list[str]) -> dict[str, Any]:
        """Execute Lua script atomically."""
        await self._ensure_connected()
        
        try:
            # Load Lua script from cache or disk (cache to avoid repeated file I/O)
            if script_path not in self._lua_script_cache:
                with open(script_path, 'r', encoding='utf-8') as f:
                    self._lua_script_cache[script_path] = f.read()
                logger.debug(f"Cached Lua script: {script_path}")
            script = self._lua_script_cache[script_path]
            
            # Execute script
            result = await self.client.eval(
                script,
                len(keys),
                *keys,
                *args
            )
            
            # Parse result (Redis returns dict or list)
            if isinstance(result, dict):
                if 'err' in result:
                    logger.warning(f"Lua script error: {result['err']}")
                return result
            
            # Convert list to dict if needed
            if isinstance(result, list) and len(result) == 2:
                return {result[0]: result[1]}
            
            return {'ok': 'SUCCESS', 'result': result}
        except RedisError as e:
            logger.error(f"Redis error executing Lua script: {e}")
            return {'err': 'REDIS_ERROR', 'message': str(e)}
        except FileNotFoundError:
            logger.error(f"Lua script not found: {script_path}")
            return {'err': 'SCRIPT_NOT_FOUND', 'message': f'Script not found: {script_path}'}
        except Exception as e:
            logger.error(f"Unexpected error executing Lua script: {e}")
            return {'err': 'UNKNOWN_ERROR', 'message': str(e)}
    
    async def cache_sku_inventory(self, sku_id: str, quantity: int, ttl: Optional[int] = None):
        """Cache SKU inventory with optional TTL."""
        await self._ensure_connected()
        
        try:
            key = f"sku:{sku_id}:inventory"
            if ttl is None:
                # No expiration - inventory is source of truth in DB
                await self.client.set(key, quantity)
            else:
                await self.client.setex(key, ttl, quantity)
            logger.debug(f"Cached SKU inventory: {sku_id} = {quantity} (TTL: {ttl})")
        except RedisError as e:
            logger.error(f"Failed to cache SKU inventory: {e}")
            raise
    
    async def get_cached_sku_inventory(self, sku_id: str) -> Optional[int]:
        """Get SKU inventory from cache."""
        await self._ensure_connected()
        
        try:
            key = f"sku:{sku_id}:inventory"
            value = await self.client.get(key)
            
            if value:
                return int(value)
            return None
        except RedisError as e:
            logger.error(f"Failed to get cached SKU inventory: {e}")
            return None
    
    async def allocate_campaign_tokens(
        self,
        campaign_id: str,
        tokens: list[str],
        total_limit: int
    ):
        """Pre-allocate tokens for a campaign."""
        await self._ensure_connected()
        
        try:
            # Add tokens to sorted set (score = timestamp for FIFO)
            pipe = self.client.pipeline()
            for i, token in enumerate(tokens):
                pipe.zadd(f"campaign:{campaign_id}:tokens", {token: i})
            
            # Set campaign metadata
            import json
            metadata = {
                "total_tokens": total_limit,
                "remaining_tokens": total_limit,
                "status": "active"
            }
            pipe.setex(f"campaign:{campaign_id}:metadata", 60, json.dumps(metadata))
            
            await pipe.execute()
            logger.info(f"Allocated {len(tokens)} tokens for campaign {campaign_id}")
        except RedisError as e:
            logger.error(f"Failed to allocate campaign tokens: {e}")
            raise
    
    async def get_campaign_status(self, campaign_id: str) -> Optional[dict[str, Any]]:
        """Get campaign status from cache."""
        await self._ensure_connected()
        
        try:
            key = f"campaign:{campaign_id}:metadata"
            value = await self.client.get(key)
            
            if value:
                import json
                return json.loads(value)
            return None
        except RedisError as e:
            logger.error(f"Failed to get campaign status: {e}")
            return None
    
    async def get_remaining_tokens(self, campaign_id: str) -> int:
        """Get remaining token count for campaign."""
        await self._ensure_connected()
        
        try:
            key = f"campaign:{campaign_id}:tokens"
            count = await self.client.zcard(key)
            return count
        except RedisError as e:
            logger.error(f"Failed to get remaining tokens: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()