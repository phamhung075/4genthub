"""
Context Caching Layer with Redis

Provides high-performance caching for context inheritance chains
and frequently accessed context data.
"""

import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import timedelta
import logging
import os

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache fallback")


class InMemoryCache:
    """Fallback in-memory cache when Redis is not available"""
    
    def __init__(self):
        self.cache = {}
        self.ttl_map = {}
        
    def get(self, key: str) -> Optional[str]:
        import time
        if key in self.cache:
            if key in self.ttl_map and time.time() > self.ttl_map[key]:
                del self.cache[key]
                del self.ttl_map[key]
                return None
            return self.cache[key]
        return None
    
    def setex(self, key: str, ttl: int, value: str):
        import time
        self.cache[key] = value
        self.ttl_map[key] = time.time() + ttl
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]
        if key in self.ttl_map:
            del self.ttl_map[key]
    
    def scan_iter(self, pattern: str):
        import re
        regex = pattern.replace('*', '.*')
        return [k for k in self.cache.keys() if re.match(regex, k)]
    
    def pipeline(self):
        return InMemoryPipeline(self)
    
    def ping(self) -> bool:
        return True


class InMemoryPipeline:
    """Pipeline for in-memory cache"""
    
    def __init__(self, cache: InMemoryCache):
        self.cache = cache
        self.operations = []
    
    def get(self, key: str):
        self.operations.append(('get', key))
        return self
    
    def setex(self, key: str, ttl: int, value: str):
        self.operations.append(('setex', key, ttl, value))
        return self
    
    def delete(self, key: str):
        self.operations.append(('delete', key))
        return self
    
    def execute(self):
        results = []
        for op in self.operations:
            if op[0] == 'get':
                results.append(self.cache.get(op[1]))
            elif op[0] == 'setex':
                self.cache.setex(op[1], op[2], op[3])
                results.append(True)
            elif op[0] == 'delete':
                self.cache.delete(op[1])
                results.append(True)
        return results


class ContextCache:
    """
    High-performance caching layer for context operations.
    Uses Redis when available, falls back to in-memory cache.
    """
    
    def __init__(self, 
                 redis_host: str = None,
                 redis_port: int = None,
                 redis_db: int = 1,
                 ttl_seconds: int = 300,
                 enable_compression: bool = True):
        """
        Initialize context cache.
        
        Args:
            redis_host: Redis host (default: localhost or env var REDIS_HOST)
            redis_port: Redis port (default: 6379 or env var REDIS_PORT)
            redis_db: Redis database number (default: 1)
            ttl_seconds: Default TTL for cached items (default: 300)
            enable_compression: Enable compression for large values
        """
        self.ttl = ttl_seconds
        self.enable_compression = enable_compression
        
        # Try to initialize Redis
        if REDIS_AVAILABLE:
            try:
                redis_host = redis_host or os.getenv('REDIS_HOST', 'localhost')
                redis_port = redis_port or int(os.getenv('REDIS_PORT', '6379'))
                
                self.redis = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1
                )
                # Test connection
                self.redis.ping()
                self.use_redis = True
                logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
                self.redis = InMemoryCache()
                self.use_redis = False
        else:
            self.redis = InMemoryCache()
            self.use_redis = False
    
    def _make_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from components"""
        parts = [prefix]
        for k, v in sorted(kwargs.items()):
            if v is not None:
                parts.append(f"{k}:{v}")
        return ":".join(parts)
    
    def _compress(self, data: str) -> str:
        """Compress data if enabled and beneficial"""
        if not self.enable_compression or len(data) < 1024:
            return data
        
        import zlib
        import base64
        compressed = zlib.compress(data.encode())
        if len(compressed) < len(data) * 0.9:  # Only use if >10% savings
            return f"COMPRESSED:{base64.b64encode(compressed).decode()}"
        return data
    
    def _decompress(self, data: str) -> str:
        """Decompress data if it was compressed"""
        if data and data.startswith("COMPRESSED:"):
            import zlib
            import base64
            compressed_data = data[11:]  # Remove "COMPRESSED:" prefix
            return zlib.decompress(base64.b64decode(compressed_data)).decode()
        return data
    
    # Context Inheritance Caching
    
    def get_inheritance_chain(self, 
                             level: str, 
                             context_id: str, 
                             user_id: str) -> Optional[Dict]:
        """Get cached inheritance chain"""
        key = self._make_key("inheritance", level=level, context_id=context_id, user_id=user_id)
        data = self.redis.get(key)
        if data:
            decompressed = self._decompress(data)
            return json.loads(decompressed)
        return None
    
    def set_inheritance_chain(self, 
                            level: str, 
                            context_id: str, 
                            user_id: str, 
                            data: Dict):
        """Cache inheritance chain with TTL"""
        key = self._make_key("inheritance", level=level, context_id=context_id, user_id=user_id)
        json_data = json.dumps(data)
        compressed = self._compress(json_data)
        self.redis.setex(key, self.ttl, compressed)
    
    def invalidate_inheritance(self, user_id: str, level: str = None, context_id: str = None):
        """Invalidate cached inheritance chains"""
        if level and context_id:
            # Invalidate specific context
            key = self._make_key("inheritance", level=level, context_id=context_id, user_id=user_id)
            self.redis.delete(key)
        else:
            # Invalidate all for user
            pattern = f"inheritance:*user_id:{user_id}*"
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
    
    # Context Data Caching
    
    def get_context(self, 
                   level: str, 
                   context_id: str, 
                   user_id: str) -> Optional[Dict]:
        """Get cached context data"""
        key = self._make_key("context", level=level, context_id=context_id, user_id=user_id)
        data = self.redis.get(key)
        if data:
            decompressed = self._decompress(data)
            return json.loads(decompressed)
        return None
    
    def set_context(self, 
                   level: str, 
                   context_id: str, 
                   user_id: str, 
                   data: Dict,
                   ttl: int = None):
        """Cache context data"""
        key = self._make_key("context", level=level, context_id=context_id, user_id=user_id)
        json_data = json.dumps(data)
        compressed = self._compress(json_data)
        self.redis.setex(key, ttl or self.ttl, compressed)
    
    def invalidate_context(self, user_id: str, level: str = None, context_id: str = None):
        """Invalidate cached context data"""
        if level and context_id:
            # Invalidate specific context
            key = self._make_key("context", level=level, context_id=context_id, user_id=user_id)
            self.redis.delete(key)
        else:
            # Invalidate all for user
            pattern = f"context:*user_id:{user_id}*"
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
    
    # Batch Operations
    
    def get_multiple_contexts(self, 
                            contexts: List[Dict[str, str]], 
                            user_id: str) -> List[Optional[Dict]]:
        """Get multiple contexts in a single operation"""
        pipeline = self.redis.pipeline()
        
        for ctx in contexts:
            key = self._make_key("context", 
                               level=ctx['level'], 
                               context_id=ctx['context_id'], 
                               user_id=user_id)
            pipeline.get(key)
        
        results = pipeline.execute()
        
        decoded_results = []
        for data in results:
            if data:
                decompressed = self._decompress(data)
                decoded_results.append(json.loads(decompressed))
            else:
                decoded_results.append(None)
        
        return decoded_results
    
    def set_multiple_contexts(self, 
                            contexts: List[Dict], 
                            user_id: str,
                            ttl: int = None):
        """Set multiple contexts in a single operation"""
        pipeline = self.redis.pipeline()
        
        for ctx in contexts:
            key = self._make_key("context",
                               level=ctx['level'],
                               context_id=ctx['context_id'],
                               user_id=user_id)
            json_data = json.dumps(ctx['data'])
            compressed = self._compress(json_data)
            pipeline.setex(key, ttl or self.ttl, compressed)
        
        pipeline.execute()
    
    # Cache Statistics
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if self.use_redis:
            try:
                info = self.redis.info('stats')
                return {
                    'type': 'redis',
                    'connected': True,
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'hit_rate': info.get('keyspace_hits', 0) / 
                               max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)),
                    'total_connections': info.get('total_connections_received', 0),
                    'rejected_connections': info.get('rejected_connections', 0)
                }
            except:
                pass
        
        return {
            'type': 'in-memory',
            'connected': True,
            'cache_size': len(self.redis.cache) if hasattr(self.redis, 'cache') else 0
        }
    
    def clear_cache(self, pattern: str = None):
        """Clear cache entries matching pattern or all"""
        if pattern:
            for key in self.redis.scan_iter(pattern):
                self.redis.delete(key)
        else:
            # Clear all cache entries
            if self.use_redis:
                self.redis.flushdb()
            else:
                self.redis.cache.clear()
                self.redis.ttl_map.clear()


# Singleton instance
_cache_instance = None

def get_context_cache() -> ContextCache:
    """Get or create singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ContextCache()
    return _cache_instance