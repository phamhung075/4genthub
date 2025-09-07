"""Cache Service Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Union
from datetime import timedelta


class ICacheService(ABC):
    """Domain interface for caching operations"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set a value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        pass
    
    @abstractmethod
    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set multiple values in cache"""
        pass
    
    @abstractmethod
    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys from cache"""
        pass
    
    @abstractmethod
    async def increment(self, key: str, delta: int = 1) -> int:
        """Increment a numeric value in cache"""
        pass
    
    @abstractmethod
    async def decrement(self, key: str, delta: int = 1) -> int:
        """Decrement a numeric value in cache"""
        pass
    
    @abstractmethod
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set expiration time for a key"""
        pass
    
    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get time-to-live for a key in seconds"""
        pass


class ICacheKeyBuilder(ABC):
    """Domain interface for building cache keys"""
    
    @abstractmethod
    def build_key(self, prefix: str, *args, **kwargs) -> str:
        """Build a cache key from components"""
        pass
    
    @abstractmethod
    def build_pattern(self, prefix: str, pattern: str) -> str:
        """Build a cache key pattern for matching"""
        pass