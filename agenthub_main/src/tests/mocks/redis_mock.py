"""Mock Redis Client for Caching Tests

Provides an in-memory Redis mock for testing caching behavior without
requiring a real Redis server.

Usage:
    >>> redis = MockRedisClient()
    >>> redis.set("key", "value", ex=60)
    >>> assert redis.get("key") == "value"
    >>> redis.delete("key")
"""

from typing import Optional, Any, Dict
from datetime import datetime, timezone, timedelta
import json


class MockRedisClient:
    """Mock Redis client with in-memory storage."""

    def __init__(self):
        """Initialize the mock Redis client."""
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """Set a key-value pair with optional expiry.

        Args:
            key: Key to set
            value: Value to store
            ex: Expiry time in seconds
            px: Expiry time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if successful, False otherwise
        """
        # Check nx/xx conditions
        exists = key in self._data
        if nx and exists:
            return False
        if xx and not exists:
            return False

        # Clean up expired entries first
        self._cleanup_expired()

        # Store value
        self._data[key] = value

        # Set expiry if specified
        if ex:
            self._expiry[key] = datetime.now(timezone.utc) + timedelta(seconds=ex)
        elif px:
            self._expiry[key] = datetime.now(timezone.utc) + timedelta(milliseconds=px)
        elif key in self._expiry:
            # Remove expiry if no expiry specified
            del self._expiry[key]

        return True

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key.

        Args:
            key: Key to retrieve

        Returns:
            Value if found and not expired, None otherwise
        """
        self._cleanup_expired()

        return self._data.get(key)

    def delete(self, *keys: str) -> int:
        """Delete one or more keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
            if key in self._expiry:
                del self._expiry[key]

        return count

    def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of keys that exist
        """
        self._cleanup_expired()

        return sum(1 for key in keys if key in self._data)

    def expire(self, key: str, seconds: int) -> bool:
        """Set an expiry time for a key.

        Args:
            key: Key to set expiry for
            seconds: Expiry time in seconds

        Returns:
            True if successful, False if key doesn't exist
        """
        if key not in self._data:
            return False

        self._expiry[key] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        return True

    def ttl(self, key: str) -> int:
        """Get the time to live for a key.

        Args:
            key: Key to check

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        if key not in self._data:
            return -2

        if key not in self._expiry:
            return -1

        ttl = (self._expiry[key] - datetime.now(timezone.utc)).total_seconds()
        return int(ttl) if ttl > 0 else -2

    def flushdb(self):
        """Clear all data from the mock database."""
        self._data.clear()
        self._expiry.clear()

    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching a pattern.

        Args:
            pattern: Pattern to match (simplified - only supports '*')

        Returns:
            List of matching keys
        """
        self._cleanup_expired()

        if pattern == "*":
            return list(self._data.keys())

        # Simple pattern matching (not full Redis glob)
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._data.keys() if k.startswith(prefix)]

        return [k for k in self._data.keys() if k == pattern]

    def incr(self, key: str) -> int:
        """Increment a key's value.

        Args:
            key: Key to increment

        Returns:
            New value after increment
        """
        current = self._data.get(key, 0)
        if not isinstance(current, int):
            raise ValueError("Value is not an integer")

        new_value = current + 1
        self._data[key] = new_value
        return new_value

    def decr(self, key: str) -> int:
        """Decrement a key's value.

        Args:
            key: Key to decrement

        Returns:
            New value after decrement
        """
        current = self._data.get(key, 0)
        if not isinstance(current, int):
            raise ValueError("Value is not an integer")

        new_value = current - 1
        self._data[key] = new_value
        return new_value

    def hset(self, name: str, key: str, value: Any) -> int:
        """Set a field in a hash.

        Args:
            name: Hash name
            key: Field key
            value: Field value

        Returns:
            1 if new field, 0 if updated existing field
        """
        if name not in self._data or not isinstance(self._data[name], dict):
            self._data[name] = {}

        is_new = key not in self._data[name]
        self._data[name][key] = value
        return 1 if is_new else 0

    def hget(self, name: str, key: str) -> Optional[Any]:
        """Get a field from a hash.

        Args:
            name: Hash name
            key: Field key

        Returns:
            Field value or None if not found
        """
        if name not in self._data or not isinstance(self._data[name], dict):
            return None

        return self._data[name].get(key)

    def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all fields and values from a hash.

        Args:
            name: Hash name

        Returns:
            Dictionary of all fields and values
        """
        if name not in self._data or not isinstance(self._data[name], dict):
            return {}

        return dict(self._data[name])

    def _cleanup_expired(self):
        """Remove expired keys."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, expiry in self._expiry.items()
            if expiry <= now
        ]

        for key in expired_keys:
            if key in self._data:
                del self._data[key]
            del self._expiry[key]
