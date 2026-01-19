"""Redis service (FULL DESIGN IMPLEMENTATION - Optimized Pool)."""

import logging
import time
from typing import Optional, Any

from redis import Redis, ResponseError, ConnectionPool
from redis.asyncio import from_url, Redis as AsyncRedis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service with optimized connection pool for high concurrency.
    
    Pool Configuration for 16 FastAPI workers + 5 background workers:
    - max_connections=100 (sufficient for 21 concurrent processes)
    - decode_responses=True (auto-decode to Python strings)
    """
    
    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0, password: str = None):
        # Optimized connection pool
        self.pool = ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=100,  # Increased for 16 workers + 5 background workers
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Create Redis client with pool
        self.client = Redis(connection_pool=self.pool)
        
        # Async Redis client (for async operations)
        self.async_client = None
    
    async def get_async_client(self):
        """Get async Redis client (lazy initialization)."""
        if self.async_client is None:
            self.async_client = await from_url(
                "redis://redis:6379/0",
                max_connections=100,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True
            )
        return self.async_client
    
    async def set(self, key: str, value: Any, ex: int = None) -> bool:
        """Set key-value pair with expiration."""
        client = await self.get_async_client()
        return await client.set(key, value, ex=ex)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        client = await self.get_async_client()
        return await client.get(key)
    
    async def hgetall(self, key: str) -> dict:
        """Get all fields and values in a hash."""
        client = await self.get_async_client()
        return await client.hgetall(key)
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get value of a hash field."""
        client = await self.get_async_client()
        return await client.hget(key, field)
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field to value."""
        client = await self.get_async_client()
        return await client.hset(key, field, value)
    
    async def hincrby(self, key: str, field: str, amount: int) -> int:
        """Increment hash field by amount."""
        client = await self.get_async_client()
        return await client.hincrby(key, field, amount)
    
    async def lpush(self, key: str, *values) -> int:
        """Push values to left of list."""
        client = await self.get_async_client()
        return await client.lpush(key, *values)
    
    async def rpop(self, key: str) -> Optional[str]:
        """Pop value from right of list."""
        client = await self.get_async_client()
        return await client.rpop(key)
    
    async def llen(self, key: str) -> int:
        """Get length of list."""
        client = await self.get_async_client()
        return await client.llen(key)
    
    async def execute_lua_script(self, script_path: str, keys: list, args: list) -> dict:
        """
        Execute Lua script.
        
        Args:
            script_path: Path to Lua script file
            keys: List of Redis keys
            args: List of arguments
        
        Returns:
            Dictionary with result or error
        """
        try:
            client = await self.get_async_client()
            
            # Read script file
            with open(script_path, 'r') as f:
                script = f.read()
            
            # Execute script
            start = time.time()
            result = await client.eval(script, len(keys), *keys, *args)
            elapsed = time.time() - start
            
            # Parse result (flat array from Lua)
            if isinstance(result, list):
                # Convert flat array to dict
                parsed = {}
                for i in range(0, len(result), 2):
                    if i + 1 < len(result):
                        parsed[result[i]] = result[i + 1]
                return parsed
            else:
                return {'result': result}
            
        except ResponseError as e:
            logger.error(f"Lua script error: {e}")
            return {'err': str(e)}
        except Exception as e:
            logger.error(f"Lua script execution failed: {e}")
            return {'err': str(e)}
    
    async def close(self):
        """Close connections."""
        if self.client:
            self.client.close()
        if self.async_client:
            await self.async_client.close()


# Global Redis service instance
redis_service = RedisService(
    host='redis',
    port=6379,
    db=0
)
