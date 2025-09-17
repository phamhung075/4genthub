"""Cache Service Adapter - Infrastructure Layer"""

from typing import Any, Optional, Dict, List, Union
from datetime import timedelta

from ...domain.interfaces.cache_service import ICacheService, ICacheKeyBuilder
from ..cache.context_cache import ContextCache


class CacheServiceAdapter(ICacheService):
    """Adapter for infrastructure cache to domain ICacheService"""
    
    def __init__(self):
        self._cache = ContextCache()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        return await self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set a value in cache with optional TTL"""
        ttl_seconds = None
        if ttl:
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
        
        result = await self._cache.set(key, value, ttl_seconds)
        return result is not None
    
    async def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        return await self._cache.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        return await self._cache.exists(key)
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        return await self._cache.clear()
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        result = {}
        for key in keys:
            value = await self._cache.get(key)
            if value is not None:
                result[key] = value
        return result
    
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set multiple values in cache"""
        ttl_seconds = None
        if ttl:
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
        
        success_count = 0
        for key, value in mapping.items():
            result = await self._cache.set(key, value, ttl_seconds)
            if result is not None:
                success_count += 1
        
        return success_count == len(mapping)
    
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys from cache"""
        deleted_count = 0
        for key in keys:
            if await self._cache.delete(key):
                deleted_count += 1
        return deleted_count
    
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache"""
        # Basic implementation - infrastructure might have better atomic operations
        current = await self._cache.get(key) or 0
        new_value = current + delta
        await self._cache.set(key, new_value)
        return new_value
    
    async def decrement(self, key: str, delta: int = 1) -> int:
        """Decrement a numeric value in cache"""
        return await self.increment(key, -delta)
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration time for a key"""
        ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
        return await self._cache.expire(key, int(ttl_seconds))
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get time-to-live for a key in seconds"""
        return await self._cache.get_ttl(key)


class CacheKeyBuilderAdapter(ICacheKeyBuilder):
    """Adapter for cache key building"""
    
    def build_key(self, prefix: str, *args, **kwargs) -> str:
        """Build a cache key from components"""
        parts = [prefix]
        parts.extend(str(arg) for arg in args)
        
        for key, value in kwargs.items():
            parts.append(f"{key}:{value}")
        
        return ":".join(parts)
    
    def build_pattern(self, prefix: str, pattern: str) -> str:
        """Build a cache key pattern for matching"""
        return f"{prefix}:{pattern}"