"""Cached Task Repository Wrapper with Automatic Invalidation

This wrapper adds Redis caching to any TaskRepository implementation.
It automatically invalidates cache on all mutation operations.
"""

import json
import os
import logging
from typing import Optional, List, Any, Dict
import redis
from redis.exceptions import RedisError

from ....domain.repositories.task_repository import TaskRepository
from ....domain.entities.task import Task
from ....domain.value_objects.task_id import TaskId

logger = logging.getLogger(__name__)


class CachedTaskRepository:
    """Wrapper that adds caching with automatic invalidation to any TaskRepository"""
    
    def __init__(self, base_repository: TaskRepository):
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
            logger.info("[CachedTaskRepository] Redis cache initialized successfully")
            return client
        except (RedisError, Exception) as e:
            logger.warning(f"[CachedTaskRepository] Redis not available, caching disabled: {e}")
            return None
    
    def _cache_key(self, key: str) -> str:
        """Generate cache key with namespace"""
        return f"task:{key}"
    
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
        if not self.enabled:
            return
        
        try:
            serialized = json.dumps(value)
            self.redis_client.setex(
                self._cache_key(key),
                self.ttl,
                serialized
            )
            logger.debug(f"[Cache] Set key: {key} with TTL: {self.ttl}s")
        except (RedisError, TypeError) as e:
            logger.warning(f"[Cache] Failed to set key {key}: {e}")
    
    # === Repository Methods with Cache Invalidation ===
    
    async def create(self, task: Task) -> Task:
        """Create task with cache invalidation"""
        result = await self.base_repo.create(task)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            # Invalidate list caches
            self._invalidate_pattern("list:*")
            # Invalidate branch-specific caches
            if hasattr(task, 'git_branch_id'):
                self._invalidate_pattern(f"branch:{task.git_branch_id}:*")
            # Invalidate project caches
            if hasattr(task, 'project_id'):
                self._invalidate_pattern(f"project:{task.project_id}:*")
            # Invalidate search caches
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated caches after creating task: {task.id if hasattr(task, 'id') else 'new'}")
        
        return result
    
    async def update(self, task: Task) -> Task:
        """Update task with cache invalidation"""
        result = await self.base_repo.update(task)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            # Invalidate specific task cache
            if hasattr(task, 'id'):
                self._invalidate_key(str(task.id))
            # Invalidate list caches
            self._invalidate_pattern("list:*")
            # Invalidate branch-specific caches
            if hasattr(task, 'git_branch_id'):
                self._invalidate_pattern(f"branch:{task.git_branch_id}:*")
            # Invalidate project caches
            if hasattr(task, 'project_id'):
                self._invalidate_pattern(f"project:{task.project_id}:*")
            # Invalidate search caches
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated caches after updating task: {task.id if hasattr(task, 'id') else 'unknown'}")
        
        return result
    
    async def delete(self, task_id: TaskId) -> bool:
        """Delete task with cache invalidation"""
        # Get task info before deletion for cache invalidation
        task = None
        try:
            task = await self.base_repo.find_by_id(task_id)
        except:
            pass
        
        result = await self.base_repo.delete(task_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            # Invalidate specific task cache
            self._invalidate_key(str(task_id))
            # Invalidate all list and search caches
            self._invalidate_pattern("*")  # Nuclear option for deletions
            logger.info(f"[Cache] Invalidated all caches after deleting task: {task_id}")
        
        return result
    
    async def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """Find task by ID with caching"""
        cache_key = str(task_id)
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            # Reconstruct Task from cached data
            return self._deserialize_task(cached)
        
        # Get from base repository
        result = await self.base_repo.find_by_id(task_id)
        
        # Cache the result if found
        if result:
            self._set_cached(cache_key, self._serialize_task(result))
        
        return result
    
    async def find_all(self) -> List[Task]:
        """Find all tasks with caching"""
        cache_key = "list:all"
        
        # Check cache first
        cached = self._get_cached(cache_key)
        if cached:
            return [self._deserialize_task(t) for t in cached]
        
        # Get from base repository
        result = await self.base_repo.find_all()
        
        # Cache the result
        self._set_cached(cache_key, [self._serialize_task(t) for t in result])
        
        return result
    
    # === Helper methods for serialization ===
    
    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serialize task to dictionary for caching"""
        # This is a simplified serialization - adjust based on your Task entity
        return {
            'id': str(task.id) if hasattr(task, 'id') else None,
            'title': task.title if hasattr(task, 'title') else None,
            'description': task.description if hasattr(task, 'description') else None,
            'status': task.status if hasattr(task, 'status') else None,
            'priority': task.priority if hasattr(task, 'priority') else None,
            'git_branch_id': task.git_branch_id if hasattr(task, 'git_branch_id') else None,
            'project_id': task.project_id if hasattr(task, 'project_id') else None,
            # Add other fields as needed
        }
    
    def _deserialize_task(self, data: Dict[str, Any]) -> Task:
        """Deserialize dictionary to Task entity"""
        # This is a simplified deserialization - adjust based on your Task entity
        # You might need to use a proper Task factory or constructor
        task = Task()
        for key, value in data.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return task
    
    # === Delegate all other methods to base repository ===
    
    def __getattr__(self, name):
        """Delegate unknown methods to base repository"""
        return getattr(self.base_repo, name)