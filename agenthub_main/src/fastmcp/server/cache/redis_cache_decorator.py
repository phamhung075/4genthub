"""
Redis Caching Decorator for API Endpoints

This module provides a caching decorator using Redis backend for API response caching.
Implements 5-minute TTL for task summaries with cache invalidation on data changes.

Author: DevOps Agent
Date: 2025-08-16
Task: API Optimization - Implement Response Caching
"""

import json
import hashlib
import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union
from datetime import timedelta
import redis
from redis.asyncio import Redis as AsyncRedis
import os

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """Manages Redis connection and caching operations"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_password: Optional[str] = None,
        default_ttl: int = 300,  # 5 minutes
        prefix: str = "api_cache"
    ):
        """
        Initialize Redis cache manager
        
        Args:
            redis_url: Redis connection URL
            redis_password: Redis password
            default_ttl: Default TTL in seconds (5 minutes)
            prefix: Cache key prefix
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_password = redis_password or os.getenv("REDIS_PASSWORD", "")
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._client: Optional[AsyncRedis] = None
        self._sync_client: Optional[redis.Redis] = None
        
    async def get_client(self) -> AsyncRedis:
        """Get or create async Redis client"""
        if not self._client:
            self._client = await AsyncRedis.from_url(
                self.redis_url,
                password=self.redis_password if self.redis_password else None,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 60,  # TCP_KEEPIDLE
                    2: 10,  # TCP_KEEPINTVL
                    3: 6,   # TCP_KEEPCNT
                }
            )
        return self._client
    
    def get_sync_client(self) -> redis.Redis:
        """Get or create sync Redis client"""
        if not self._sync_client:
            self._sync_client = redis.from_url(
                self.redis_url,
                password=self.redis_password if self.redis_password else None,
                decode_responses=True
            )
        return self._sync_client
    
    def generate_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate cache key from endpoint and parameters
        
        Args:
            endpoint: API endpoint name
            params: Request parameters
            
        Returns:
            Cache key string
        """
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{self.prefix}:{endpoint}:{param_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.warning(f"Cache GET error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        try:
            client = await self.get_client()
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache SET error: {e}")
            return False
    
    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "api_cache:tasks:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cache INVALIDATE: {deleted} keys matching {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache INVALIDATE error: {e}")
            return 0
    
    async def flush_all(self) -> bool:
        """Flush all cache entries with prefix"""
        try:
            deleted = await self.invalidate(f"{self.prefix}:*")
            logger.info(f"Cache FLUSH: {deleted} keys deleted")
            return True
        except Exception as e:
            logger.warning(f"Cache FLUSH error: {e}")
            return False
    
    async def close(self):
        """Close Redis connections"""
        if self._client:
            await self._client.close()
        if self._sync_client:
            self._sync_client.close()


# Global cache manager instance
_cache_manager: Optional[RedisCacheManager] = None


def get_cache_manager() -> RedisCacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    if not _cache_manager:
        _cache_manager = RedisCacheManager()
    return _cache_manager


def redis_cache(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    invalidate_on: Optional[list] = None
):
    """
    Decorator for caching API endpoint responses in Redis
    
    Args:
        ttl: Time-to-live in seconds (default: 300 seconds / 5 minutes)
        key_prefix: Custom key prefix for this endpoint
        invalidate_on: List of actions that should invalidate this cache
        
    Example:
        @redis_cache(ttl=300, key_prefix="task_summaries")
        async def get_task_summaries(request):
            # Expensive operation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # Extract endpoint name
            endpoint = key_prefix or func.__name__
            
            # Build cache key from args/kwargs
            cache_params = {
                "args": str(args),
                "kwargs": str(kwargs)
            }
            cache_key = cache_manager.generate_cache_key(endpoint, cache_params)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache successful results
            if result:
                await cache_manager.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            sync_client = cache_manager.get_sync_client()
            
            # Extract endpoint name
            endpoint = key_prefix or func.__name__
            
            # Build cache key from args/kwargs
            cache_params = {
                "args": str(args),
                "kwargs": str(kwargs)
            }
            cache_key = cache_manager.generate_cache_key(endpoint, cache_params)
            
            # Try to get from cache
            try:
                cached_value = sync_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return json.loads(cached_value)
                logger.debug(f"Cache MISS: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache GET error: {e}")
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Cache successful results
            if result:
                try:
                    serialized = json.dumps(result)
                    sync_client.setex(cache_key, ttl or 300, serialized)
                    logger.debug(f"Cache SET: {cache_key}")
                except Exception as e:
                    logger.warning(f"Cache SET error: {e}")
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CacheInvalidator:
    """Handles cache invalidation on data changes"""
    
    @staticmethod
    async def invalidate_task_cache(task_id: Optional[str] = None):
        """Invalidate task-related cache entries"""
        cache_manager = get_cache_manager()
        
        if task_id:
            # Invalidate specific task
            patterns = [
                f"api_cache:*task*:{task_id}:*",
                f"api_cache:*task*:*{task_id}*"
            ]
        else:
            # Invalidate all task caches
            patterns = [
                "api_cache:*task*:*",
                "api_cache:*summaries*:*"
            ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await cache_manager.invalidate(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} task cache entries")
        return total_deleted
    
    @staticmethod
    async def invalidate_subtask_cache(parent_task_id: Optional[str] = None):
        """Invalidate subtask-related cache entries"""
        cache_manager = get_cache_manager()
        
        if parent_task_id:
            patterns = [
                f"api_cache:*subtask*:{parent_task_id}:*",
                f"api_cache:*subtask*:*{parent_task_id}*"
            ]
        else:
            patterns = ["api_cache:*subtask*:*"]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await cache_manager.invalidate(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} subtask cache entries")
        return total_deleted
    
    @staticmethod
    async def invalidate_context_cache(context_id: Optional[str] = None):
        """Invalidate context-related cache entries"""
        cache_manager = get_cache_manager()
        
        if context_id:
            patterns = [
                f"api_cache:*context*:{context_id}:*",
                f"api_cache:*context*:*{context_id}*"
            ]
        else:
            patterns = ["api_cache:*context*:*"]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await cache_manager.invalidate(pattern)
            total_deleted += deleted
        
        logger.info(f"Invalidated {total_deleted} context cache entries")
        return total_deleted


# Performance monitoring
class CacheMetrics:
    """Track cache performance metrics"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.invalidations = 0
        self.errors = 0
        
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "invalidations": self.invalidations,
            "errors": self.errors,
            "hit_rate": f"{self.hit_rate:.2f}%"
        }
    
    def reset(self):
        """Reset metrics"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.invalidations = 0
        self.errors = 0


# Global metrics instance
cache_metrics = CacheMetrics()