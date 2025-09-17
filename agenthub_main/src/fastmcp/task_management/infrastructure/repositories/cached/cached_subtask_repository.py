"""Cached Subtask Repository Wrapper with Automatic Invalidation

This wrapper adds Redis caching to any SubtaskRepository implementation.
It automatically invalidates cache on all mutation operations.
"""

import json
import os
import logging
from typing import Optional, List, Any, Dict
import redis
from redis.exceptions import RedisError

from ....domain.repositories.subtask_repository import SubtaskRepository
from ....domain.entities.subtask import Subtask

logger = logging.getLogger(__name__)


class CachedSubtaskRepository:
    """Wrapper that adds caching with automatic invalidation to any SubtaskRepository"""
    
    def __init__(self, base_repository: SubtaskRepository):
        """Initialize cached repository wrapper
        
        Args:
            base_repository: The underlying repository to wrap with caching
        """
        self.base_repo = base_repository
        self.redis_client = self._init_redis()
        self.ttl = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes default
        self.enabled = self.redis_client is not None
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection with fallback"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                password=os.getenv('REDIS_PASSWORD'),
                db=int(os.getenv('REDIS_DB', '0')),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            client.ping()
            logger.info("[CachedSubtaskRepository] Redis cache initialized successfully")
            return client
        except (RedisError, Exception) as e:
            logger.warning(f"[CachedSubtaskRepository] Redis not available, caching disabled: {e}")
            return None
    
    def _cache_key(self, key: str) -> str:
        """Generate cache key with namespace"""
        return f"subtask:{key}"
    
    def _invalidate_key(self, key: str):
        """Delete specific cache key"""
        if self.enabled:
            try:
                self.redis_client.delete(self._cache_key(key))
                logger.debug(f"[Cache] Invalidated key: {key}")
            except RedisError as e:
                logger.warning(f"[Cache] Failed to invalidate key {key}: {e}")
    
    def _invalidate_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if self.enabled:
            try:
                # Use SCAN to find keys matching pattern
                full_pattern = self._cache_key(pattern)
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor, match=full_pattern, count=100)
                    if keys:
                        self.redis_client.delete(*keys)
                        logger.debug(f"[Cache] Invalidated {len(keys)} keys matching pattern: {pattern}")
                    if cursor == 0:
                        break
            except RedisError as e:
                logger.warning(f"[Cache] Failed to invalidate pattern {pattern}: {e}")
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            cached = self.redis_client.get(self._cache_key(key))
            if cached:
                logger.debug(f"[Cache] Hit for key: {key}")
                return json.loads(cached)
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"[Cache] Failed to get key {key}: {e}")
        
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Set value in cache with TTL"""
        if self.enabled:
            try:
                self.redis_client.setex(
                    self._cache_key(key),
                    self.ttl,
                    json.dumps(value, default=str)
                )
                logger.debug(f"[Cache] Set key: {key} with TTL: {self.ttl}")
            except (RedisError, json.JSONEncodeError) as e:
                logger.warning(f"[Cache] Failed to set key {key}: {e}")
    
    # === Delegated Methods with Caching ===
    
    def get_by_id(self, subtask_id: str) -> Optional[Subtask]:
        """Get subtask by ID with caching"""
        cache_key = f"id:{subtask_id}"
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            return Subtask(**cached) if cached else None
        
        # Fetch from base repo
        result = self.base_repo.get_by_id(subtask_id)
        
        # Cache the result
        if result:
            self._set_cached(cache_key, result.__dict__ if hasattr(result, '__dict__') else result)
        
        return result
    
    def get_by_task_id(self, task_id: str) -> List[Subtask]:
        """Get all subtasks for a task with caching"""
        cache_key = f"task:{task_id}"
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            return [Subtask(**s) if isinstance(s, dict) else s for s in cached]
        
        # Fetch from base repo
        result = self.base_repo.get_by_task_id(task_id)
        
        # Cache the result
        if result:
            self._set_cached(cache_key, [s.__dict__ if hasattr(s, '__dict__') else s for s in result])
        
        return result

    def find_by_parent_task_id(self, parent_task_id) -> List[Subtask]:
        """Find all subtasks for a parent task with caching"""
        # Convert to string if it's a TaskId object
        task_id_str = parent_task_id.value if hasattr(parent_task_id, 'value') else str(parent_task_id)
        cache_key = f"parent_task:{task_id_str}"
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"[Cache] Hit for find_by_parent_task_id: {task_id_str}")
            return [Subtask(**s) if isinstance(s, dict) else s for s in cached]
        
        # Fetch from base repo
        logger.info(f"[CachedSubtaskRepository] Cache miss, delegating find_by_parent_task_id to base repo for task: {task_id_str}")
        result = self.base_repo.find_by_parent_task_id(parent_task_id)
        
        # Cache the result
        if result is not None:
            serializable_result = []
            for subtask in result:
                if hasattr(subtask, '__dict__'):
                    serializable_result.append(subtask.__dict__)
                elif hasattr(subtask, 'to_dict'):
                    serializable_result.append(subtask.to_dict())
                else:
                    serializable_result.append(subtask)
            
            self._set_cached(cache_key, serializable_result)
            logger.debug(f"[Cache] Cached {len(result)} subtasks for parent_task: {task_id_str}")
        
        return result
    
    def create(self, subtask: Subtask) -> Subtask:
        """Create subtask with cache invalidation"""
        result = self.base_repo.create(subtask)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_pattern(f"task:{subtask.task_id}:*")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            # Also invalidate parent task cache
            self._invalidate_pattern(f"task:id:{subtask.task_id}")
            logger.info(f"[Cache] Invalidated subtask caches after create")
        
        return result
    
    def update(self, subtask: Subtask) -> Subtask:
        """Update subtask with cache invalidation"""
        result = self.base_repo.update(subtask)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{subtask.id}")
            self._invalidate_pattern(f"task:{subtask.task_id}:*")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            # Also invalidate parent task cache
            self._invalidate_pattern(f"task:id:{subtask.task_id}")
            logger.info(f"[Cache] Invalidated subtask caches after update")
        
        return result
    
    def delete(self, subtask_id: str) -> bool:
        """Delete subtask with cache invalidation"""
        # Get subtask details for invalidation before deletion
        subtask = self.get_by_id(subtask_id)
        
        result = self.base_repo.delete(subtask_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{subtask_id}")
            if subtask:
                self._invalidate_pattern(f"task:{subtask.task_id}:*")
                # Also invalidate parent task cache
                self._invalidate_pattern(f"task:id:{subtask.task_id}")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated subtask caches after delete")
        
        return result
    
    def delete_by_parent_task_id(self, task_id: str) -> int:
        """Delete all subtasks for a task with cache invalidation"""
        result = self.base_repo.delete_by_parent_task_id(task_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_pattern(f"task:{task_id}:*")
            self._invalidate_pattern("subtask:*")  # Nuclear option for safety
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            # Also invalidate parent task cache
            self._invalidate_pattern(f"task:id:{task_id}")
            logger.info(f"[Cache] Invalidated all subtask caches after bulk delete")
        
        return result
    
    def remove_subtask(self, subtask_id: str) -> bool:
        """Remove subtask with cache invalidation"""
        # Get subtask details for invalidation
        subtask = self.get_by_id(subtask_id)
        
        result = self.base_repo.remove_subtask(subtask_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{subtask_id}")
            if subtask:
                self._invalidate_pattern(f"task:{subtask.task_id}:*")
                # Also invalidate parent task cache  
                self._invalidate_pattern(f"task:id:{subtask.task_id}")
            self._invalidate_pattern("list:*")
            logger.info(f"[Cache] Invalidated subtask caches after remove")
        
        return result
    
    def update_progress(self, subtask_id: str, progress_percentage: int, progress_notes: str = None) -> Subtask:
        """Update subtask progress with cache invalidation"""
        # Get subtask details for invalidation
        subtask = self.get_by_id(subtask_id)
        
        result = self.base_repo.update_progress(subtask_id, progress_percentage, progress_notes)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{subtask_id}")
            if subtask:
                self._invalidate_pattern(f"task:{subtask.task_id}:*")
                # Also invalidate parent task cache
                self._invalidate_pattern(f"task:id:{subtask.task_id}")
            logger.info(f"[Cache] Invalidated subtask caches after progress update")
        
        return result
    
    # === Delegate all other methods to base repository ===
    
    def __getattr__(self, name):
        """Delegate any unimplemented methods to base repository"""
        return getattr(self.base_repo, name)