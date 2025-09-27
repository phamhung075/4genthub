"""Performance Configuration for Task Management

This module provides configuration settings for performance optimizations.
"""

import os
from typing import Dict, Any


class PerformanceConfig:
    """Performance configuration settings"""
    
    # Cache settings
    CACHE_ENABLED = os.getenv('TASK_CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_TTL_SECONDS = int(os.getenv('TASK_CACHE_TTL', '300'))  # 5 minutes default
    CACHE_MAX_SIZE = int(os.getenv('TASK_CACHE_MAX_SIZE', '1000'))
    
    # Query optimization settings
    USE_SELECTINLOAD = os.getenv('USE_SELECTINLOAD', 'true').lower() == 'true'
    QUERY_TIMEOUT_MS = int(os.getenv('QUERY_TIMEOUT_MS', '5000'))  # 5 seconds default
    
    # Pagination settings
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
    MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '200'))
    
    # Response optimization
    MINIMAL_RESPONSE_MODE = os.getenv('MINIMAL_RESPONSE_MODE', 'true').lower() == 'true'
    COMPRESS_RESPONSES = os.getenv('COMPRESS_RESPONSES', 'false').lower() == 'true'
    
    # Database optimization
    CONNECTION_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
    CONNECTION_POOL_OVERFLOW = int(os.getenv('DB_POOL_OVERFLOW', '10'))
    CONNECTION_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    
    # Performance monitoring
    ENABLE_QUERY_LOGGING = os.getenv('ENABLE_QUERY_LOGGING', 'false').lower() == 'true'
    SLOW_QUERY_THRESHOLD_MS = int(os.getenv('SLOW_QUERY_THRESHOLD_MS', '1000'))
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration settings as dictionary
        
        Returns:
            Dictionary of configuration settings
        """
        return {
            'cache': {
                'enabled': cls.CACHE_ENABLED,
                'ttl_seconds': cls.CACHE_TTL_SECONDS,
                'max_size': cls.CACHE_MAX_SIZE
            },
            'query': {
                'use_selectinload': cls.USE_SELECTINLOAD,
                'timeout_ms': cls.QUERY_TIMEOUT_MS
            },
            'pagination': {
                'default_size': cls.DEFAULT_PAGE_SIZE,
                'max_size': cls.MAX_PAGE_SIZE
            },
            'response': {
                'minimal_mode': cls.MINIMAL_RESPONSE_MODE,
                'compress': cls.COMPRESS_RESPONSES
            },
            'database': {
                'pool_size': cls.CONNECTION_POOL_SIZE,
                'pool_overflow': cls.CONNECTION_POOL_OVERFLOW,
                'pool_timeout': cls.CONNECTION_POOL_TIMEOUT
            },
            'monitoring': {
                'enable_query_logging': cls.ENABLE_QUERY_LOGGING,
                'slow_query_threshold_ms': cls.SLOW_QUERY_THRESHOLD_MS
            }
        }
    
    @classmethod
    def is_performance_mode(cls) -> bool:
        """Check if performance optimizations are enabled
        
        Returns:
            True if performance mode is enabled
        """
        # FORCE PERFORMANCE MODE FOR IMMEDIATE FIX
        # This addresses the 5-second delay issue with Supabase
        return True  # Always use performance optimizations
        # Original: return cls.CACHE_ENABLED and cls.MINIMAL_RESPONSE_MODE