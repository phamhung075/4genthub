"""Cache Manager for Performance Optimization

This module provides a flexible caching layer to reduce database queries
and improve response times for frequently accessed data.
"""

import time
import json
import hashlib
import logging
import threading
from typing import Any, Dict, Optional, Callable, Union, List
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry"""
    key: str
    value: Any
    created_at: float
    ttl: int
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        if self.ttl <= 0:  # No expiration
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def increment_hits(self):
        """Increment hit counter"""
        self.hits += 1


class CacheManager:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - TTL (Time To Live) support
    - LRU eviction when size limit reached
    - Thread-safe operations
    - Cache statistics
    - Flexible key generation
    - Batch operations
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return None
                
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.increment_hits()
            self._stats['hits'] += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None uses default)
        """
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Check if we need to evict
            if len(self._cache) >= self._max_size:
                # Evict least recently used
                evicted_key = next(iter(self._cache))
                del self._cache[evicted_key]
                self._stats['evictions'] += 1
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl if ttl is not None else self._default_ttl
            )
            self._cache[key] = entry
            self._stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
            
            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self._max_size,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1
            
            return len(expired_keys)


# Global cache instances
_cache_instances: Dict[str, CacheManager] = {}
_cache_lock = threading.Lock()


def get_cache(name: str = 'default', **kwargs) -> CacheManager:
    """
    Get or create a named cache instance.
    
    Args:
        name: Cache name
        **kwargs: Arguments for CacheManager if creating new
        
    Returns:
        CacheManager instance
    """
    with _cache_lock:
        if name not in _cache_instances:
            _cache_instances[name] = CacheManager(**kwargs)
            logger.info(f"Created cache '{name}' with {kwargs}")
        
        return _cache_instances[name]


def cached(
    ttl: int = 300,
    cache_name: str = 'default',
    key_func: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        cache_name: Name of cache to use
        key_func: Custom key generation function
        condition: Function to determine if result should be cached
        
    Usage:
        @cached(ttl=600)
        def get_user(user_id: str):
            return database.get_user(user_id)
            
        @cached(ttl=300, key_func=lambda task_id: f"task:{task_id}")
        def get_task(task_id: str):
            return repository.find_by_id(task_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__module__, func.__name__]
                
                # Add args to key
                for arg in args:
                    if isinstance(arg, (str, int, float, bool)):
                        key_parts.append(str(arg))
                    else:
                        # Hash complex objects
                        key_parts.append(hashlib.md5(
                            json.dumps(str(arg), sort_keys=True).encode()
                        ).hexdigest()[:8])
                
                # Add kwargs to key
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                
                cache_key = ":".join(key_parts)
            
            # Get cache instance
            cache = get_cache(cache_name)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_value
            
            # Call function
            result = func(*args, **kwargs)
            
            # Cache result if condition met
            if condition is None or condition(result):
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {func.__name__} with key {cache_key}")
            
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: get_cache(cache_name).clear()
        wrapper.cache_delete = lambda *args, **kwargs: get_cache(cache_name).delete(
            key_func(*args, **kwargs) if key_func else None
        )
        wrapper.cache_stats = lambda: get_cache(cache_name).get_stats()
        
        return wrapper
    
    return decorator


class CachedRepository:
    """
    Mixin class for adding caching to repositories.
    
    Usage:
        class TaskRepository(CachedRepository, BaseRepository):
            @cached_method(ttl=300)
            def find_by_id(self, task_id: str):
                return super().find_by_id(task_id)
    """
    
    def __init__(self, *args, cache_name: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_name = cache_name or f"{self.__class__.__name__}_cache"
        self._cache = get_cache(self._cache_name)
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate cache entries.
        
        Args:
            pattern: Key pattern to match (None clears all)
        """
        if pattern is None:
            self._cache.clear()
        else:
            # Simple pattern matching
            with self._cache._lock:
                keys_to_delete = [
                    key for key in self._cache._cache.keys()
                    if pattern in key
                ]
                for key in keys_to_delete:
                    self._cache.delete(key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get repository cache statistics"""
        return self._cache.get_stats()


def cached_method(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator for caching repository methods.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Optional prefix for cache keys
        
    Usage:
        @cached_method(ttl=600)
        def find_by_criteria(self, criteria: Dict):
            return self._execute_query(...)
    """
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            key_parts = [
                key_prefix or f"{self.__class__.__name__}:{method.__name__}"
            ]
            
            # Add args
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    key_parts.append(str(arg))
                else:
                    key_parts.append(hashlib.md5(
                        json.dumps(str(arg), sort_keys=True).encode()
                    ).hexdigest()[:8])
            
            cache_key = ":".join(key_parts)
            
            # Use instance cache
            cache = getattr(self, '_cache', get_cache('default'))
            
            # Try cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call method
            result = method(self, *args, **kwargs)
            
            # Cache result
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator