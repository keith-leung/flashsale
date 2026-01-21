# Redis connection manager for distributed locking across 3 Redis nodes

import redis
import hashlib
from typing import List, Optional
from ..core.config import settings

class RedisManager:
    """Manages connections to 3 Redis nodes for distributed locking."""
    
    def __init__(self, node_urls: List[str] = None):
        """Initialize Redis connections to 3 nodes."""
        if node_urls is None:
            node_urls = [
                settings.redis_node1_url,
                settings.redis_node2_url,
                settings.redis_node3_url
            ]
        
        self.nodes = [redis.Redis.from_url(url) for url in node_urls]
        self.node_urls = node_urls
        self._validate_nodes()
    
    def _validate_nodes(self):
        """Validate that all Redis nodes are connected."""
        for i, node in enumerate(self.nodes):
            try:
                node.ping()
            except Exception as e:
                raise ConnectionError(f"Cannot connect to Redis node {i+1} at {self.node_urls[i]}: {e}")
    
    def get_node_for_sku(self, sku_id: str) -> redis.Redis:
        """
        Get the Redis node responsible for a specific SKU.
        
        Uses consistent hashing for SKU-range partitioning across 3 nodes.
        Single-SKU orders use fast-path (single node lock).
        Multi-SKU orders may need multi-node locks.
        """
        hash_val = int(hashlib.md5(sku_id.encode()).hexdigest(), 16)
        node_idx = hash_val % len(self.nodes)
        return self.nodes[node_idx]
    
    def get_nodes_for_skus(self, sku_ids: List[str]) -> List[redis.Redis]:
        """
        Get unique Redis nodes for multiple SKUs (for multi-SKU orders).
        Only returns unique nodes to avoid redundant locking.
        """
        nodes = set()
        for sku_id in sku_ids:
            nodes.add(self.get_node_for_sku(sku_id))
        return list(nodes)
    
    async def acquire_single_node_lock(self, resource: str, ttl_ms: int, sku_id: str = None) -> Optional[object]:
        """
        Acquire a single-node lock (fast path for single-SKU orders).
        
        Args:
            resource: The resource to lock (e.g., SKU ID)
            ttl_ms: Lock TTL in milliseconds
            sku_id: Optional SKU ID for node selection (defaults to resource if not provided)
            
        Returns:
            Lock object if acquired, None if failed
        """
        if sku_id is None:
            sku_id = resource
        
        node = self.get_node_for_sku(sku_id)
        lock = self._create_redis_lock(node, resource, ttl_ms)
        
        # Use blocking acquire with 50ms timeout for concurrent requests
        if await lock.acquire(blocking=True, blocking_timeout_ms=50):
            return lock
        return None
    
    async def acquire_multi_node_lock(self, resource: str, ttl_ms: int, sku_ids: List[str]) -> Optional[List]:
        """
        Acquire locks on multiple nodes for multi-SKU orders.
        Only returns unique nodes to avoid redundant locking.
        
        Args:
            resource: The resource to lock
            ttl_ms: Lock TTL in milliseconds
            sku_ids: List of SKU IDs to cover
            
        Returns:
            List of locks if all acquired, None if any failed
        """
        nodes = self.get_nodes_for_skus(sku_ids)
        
        if len(nodes) == 1:
            # Only one node involved, use single-node lock
            return await self.acquire_single_node_lock(resource, ttl_ms, sku_ids[0])
        
        # Multiple nodes - acquire locks on all with short timeout
        locks = []
        for node in nodes:
            lock = self._create_redis_lock(node, resource, ttl_ms)
            if await lock.acquire(blocking=True, blocking_timeout_ms=20):
                locks.append(lock)
            else:
                # Failed to get one lock, release any we already acquired
                for acquired_lock in locks:
                    await acquired_lock.release()
                return None
        
        return locks
    
    def _create_redis_lock(self, node, resource, ttl_ms):
        """Create a Redis lock object."""
        from .distributed_lock import RedisLock
        # Use milliseconds for better precision, minimum 50ms
        ttl_ms = max(50, ttl_ms)
        return RedisLock(node, resource, ttl_ms)
    
    async def release_lock(self, lock):
        """Release a previously acquired lock."""
        if lock:
            if isinstance(lock, list):
                # Multi-node lock - release all
                for l in lock:
                    await l.release()
            else:
                # Single-node lock
                await lock.release()

# Global Redis manager instance
redis_manager = RedisManager()
