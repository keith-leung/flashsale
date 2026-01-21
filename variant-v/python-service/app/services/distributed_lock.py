# Distributed lock service with SKU-based routing

import asyncio
from typing import Optional, List
from .redis_manager import redis_manager
from ..core.config import settings

class DistributedLockService:
    """Service for managing distributed locks with SKU-based routing."""
    
    def __init__(self):
        self.redis_manager = redis_manager
    
    async def acquire(self, resource: str, sku_id: str, ttl_ms: int = None) -> Optional[object]:
        """
        Acquire a distributed lock for a single SKU.
        
        Args:
            resource: The resource to lock
            sku_id: SKU ID for node selection
            ttl_ms: Lock TTL in milliseconds (uses default if None)
            
        Returns:
            Lock object if acquired, None if failed
        """
        if ttl_ms is None:
            ttl_ms = settings.default_lock_ttl_ms
        
        return await self.redis_manager.acquire_single_node_lock(resource, ttl_ms, sku_id)
    
    async def acquire_multi(self, resource: str, sku_ids: List[str], ttl_ms: int = None) -> Optional[object]:
        """
        Acquire distributed locks for multiple SKUs (multi-SKU orders).
        
        Args:
            resource: The resource to lock
            sku_ids: List of SKU IDs to cover
            ttl_ms: Lock TTL in milliseconds (uses default if None)
            
        Returns:
            List of locks if all acquired, None if any failed
        """
        if ttl_ms is None:
            ttl_ms = settings.default_lock_ttl_ms
        
        return await self.redis_manager.acquire_multi_node_lock(resource, ttl_ms, sku_ids)
    
    async def release(self, lock):
        """Release a previously acquired lock."""
        if lock:
            await self.redis_manager.release_lock(lock)
    
    async def acquire_with_retry(self, resource: str, sku_id: str, ttl_ms: int = None) -> Optional[object]:
        """
        Acquire lock with retry logic.
        
        Args:
            resource: The resource to lock
            sku_id: SKU ID for node selection
            ttl_ms: Lock TTL in milliseconds
            
        Returns:
            Lock object if acquired after retries, None if all retries failed
        """
        if ttl_ms is None:
            ttl_ms = settings.default_lock_ttl_ms
        
        for attempt in range(settings.lock_retry_count):
            lock = await self.acquire(resource, sku_id, ttl_ms)
            if lock:
                return lock
            
            # Exponential backoff
            wait_ms = 2  # 2ms fixed for fast retry
            await asyncio.sleep(wait_ms / 1000.0)
        
        return None
    
    async def is_locked(self, resource: str, sku_id: str) -> bool:
        """
        Check if a resource is currently locked.
        
        Args:
            resource: The resource to check
            sku_id: SKU ID for node selection
            
        Returns:
            bool: True if locked, False otherwise
        """
        node = self.redis_manager.get_node_for_sku(sku_id)
        lock_key = f"lock:{resource}"
        return node.exists(lock_key)

class RedisLock:
    """Async Redis lock implementation."""
    
    def __init__(self, redis_client, resource, ttl_ms):
        self.redis = redis_client
        self.resource = resource
        self.ttl_ms = ttl_ms
        self.key = f"lock:{resource}"
        self.acquired = False
        self.token = None
    
    async def acquire(self, blocking=True, blocking_timeout_ms=100):
        """
        Acquire the lock asynchronously.
        
        Args:
            blocking: Whether to wait for lock if not immediately available
            blocking_timeout_ms: Max time to wait in milliseconds
            
        Returns:
            bool: True if lock acquired, False otherwise
        """
        import uuid
        import time
        
        start_time = time.time()
        self.token = str(uuid.uuid4())
        
        while True:
            # Try to acquire lock with NX (only if not exists) and PX (milliseconds)
            result = self.redis.set(self.key, self.token, nx=True, px=self.ttl_ms)
            
            if result:
                self.acquired = True
                return True
            
            if not blocking:
                return False
            
            # Check timeout
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > blocking_timeout_ms:
                return False
            
            # Wait with asyncio to avoid blocking event loop
            await asyncio.sleep(0.001)  # 1ms sleep
    
    async def release(self):
        """Release the lock asynchronously."""
        if self.acquired:
            # Use Lua script to release only if we own the lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            self.redis.eval(lua_script, 1, self.key, self.token)
            self.acquired = False
            self.token = None
class LockGuard:
    """
    Async context manager for automatic lock acquisition and release.
    
    Usage:
        async with LockGuard(distributed_lock, "sku_123", "sku_123") as lock:
            if lock:
                # Critical section - lock acquired
                pass
            else:
                # Failed to acquire lock
                raise HTTPException(409, "Resource busy")
    """
    
    def __init__(self, lock_service: DistributedLockService, resource: str, sku_id: str, ttl_ms: int = None):
        self.lock_service = lock_service
        self.resource = resource
        self.sku_id = sku_id
        self.ttl_ms = ttl_ms
        self.lock = None
    
    async def __aenter__(self):
        self.lock = await self.lock_service.acquire_with_retry(
            self.resource, self.sku_id, self.ttl_ms
        )
        return self.lock
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            await self.lock_service.release(self.lock)

# Global distributed lock service instance
distributed_lock = DistributedLockService()
