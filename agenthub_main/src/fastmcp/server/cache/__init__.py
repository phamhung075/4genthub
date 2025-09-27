"""
Redis Cache Module for API Response Caching

This module provides Redis-based caching for API endpoints with automatic
cache invalidation on data changes.

Author: DevOps Agent
Date: 2025-08-16
"""

from .redis_cache_decorator import (
    RedisCacheManager,
    get_cache_manager,
    redis_cache,
    CacheInvalidator,
    CacheMetrics,
    cache_metrics
)

from .cache_invalidation_hooks import (
    CacheInvalidationHooks,
    cache_invalidation_decorator,
    register_cache_invalidation_hooks
)

__all__ = [
    'RedisCacheManager',
    'get_cache_manager',
    'redis_cache',
    'CacheInvalidator',
    'CacheMetrics',
    'cache_metrics',
    'CacheInvalidationHooks',
    'cache_invalidation_decorator',
    'register_cache_invalidation_hooks'
]