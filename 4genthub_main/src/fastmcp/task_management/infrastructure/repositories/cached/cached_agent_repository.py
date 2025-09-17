"""Cached Agent Repository Wrapper with Automatic Invalidation

This wrapper adds Redis caching to any AgentRepository implementation.
It automatically invalidates cache on all mutation operations.
"""

import json
import os
import logging
from typing import Optional, List, Any, Dict
import redis
from redis.exceptions import RedisError

from ....domain.repositories.agent_repository import AgentRepository
from ....domain.entities.agent import Agent

logger = logging.getLogger(__name__)


class CachedAgentRepository:
    """Wrapper that adds caching with automatic invalidation to any AgentRepository"""
    
    def __init__(self, base_repository: AgentRepository):
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
            logger.info("[CachedAgentRepository] Redis cache initialized successfully")
            return client
        except (RedisError, Exception) as e:
            logger.warning(f"[CachedAgentRepository] Redis not available, caching disabled: {e}")
            return None
    
    def _cache_key(self, key: str) -> str:
        """Generate cache key with namespace"""
        return f"agent:{key}"
    
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
    
    def get_by_id(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID with caching"""
        cache_key = f"id:{agent_id}"
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            return Agent(**cached) if cached else None
        
        # Fetch from base repo
        result = self.base_repo.get_by_id(agent_id)
        
        # Cache the result
        if result:
            self._set_cached(cache_key, result.__dict__ if hasattr(result, '__dict__') else result)
        
        return result
    
    def get_by_project_id(self, project_id: str) -> List[Agent]:
        """Get all agents for a project with caching"""
        cache_key = f"project:{project_id}"
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached:
            return [Agent(**a) if isinstance(a, dict) else a for a in cached]
        
        # Fetch from base repo
        result = self.base_repo.get_by_project_id(project_id)
        
        # Cache the result
        if result:
            self._set_cached(cache_key, [a.__dict__ if hasattr(a, '__dict__') else a for a in result])
        
        return result
    
    def register_agent(self, agent: Agent) -> Agent:
        """Register agent with cache invalidation"""
        result = self.base_repo.register_agent(agent)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_pattern(f"project:{agent.project_id}:*")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated agent caches after register")
        
        return result
    
    def update_agent(self, agent: Agent) -> Agent:
        """Update agent with cache invalidation"""
        result = self.base_repo.update_agent(agent)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{agent.id}")
            self._invalidate_pattern(f"project:{agent.project_id}:*")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated agent caches after update")
        
        return result
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister agent with cache invalidation"""
        # Get agent details for invalidation before deletion
        agent = self.get_by_id(agent_id)
        
        result = self.base_repo.unregister_agent(agent_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{agent_id}")
            if agent:
                self._invalidate_pattern(f"project:{agent.project_id}:*")
            self._invalidate_pattern("list:*")
            self._invalidate_pattern("search:*")
            logger.info(f"[Cache] Invalidated agent caches after unregister")
        
        return result
    
    def assign_agent(self, agent_id: str, git_branch_id: str) -> bool:
        """Assign agent to branch with cache invalidation"""
        # Get agent details for invalidation
        agent = self.get_by_id(agent_id)
        
        result = self.base_repo.assign_agent(agent_id, git_branch_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{agent_id}")
            if agent:
                self._invalidate_pattern(f"project:{agent.project_id}:*")
            self._invalidate_pattern(f"branch:{git_branch_id}:*")
            self._invalidate_pattern("assignments:*")
            logger.info(f"[Cache] Invalidated agent caches after assign")
        
        return result
    
    def unassign_agent(self, agent_id: str, git_branch_id: str) -> bool:
        """Unassign agent from branch with cache invalidation"""
        # Get agent details for invalidation
        agent = self.get_by_id(agent_id)
        
        result = self.base_repo.unassign_agent(agent_id, git_branch_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_key(f"id:{agent_id}")
            if agent:
                self._invalidate_pattern(f"project:{agent.project_id}:*")
            self._invalidate_pattern(f"branch:{git_branch_id}:*")
            self._invalidate_pattern("assignments:*")
            logger.info(f"[Cache] Invalidated agent caches after unassign")
        
        return result
    
    def rebalance_agents(self, project_id: str) -> Dict[str, Any]:
        """Rebalance agents for project with cache invalidation"""
        result = self.base_repo.rebalance_agents(project_id)
        
        # INVALIDATE CACHE (CRITICAL!)
        if self.enabled:
            self._invalidate_pattern(f"project:{project_id}:*")
            self._invalidate_pattern("agent:*")  # Nuclear option for safety
            self._invalidate_pattern("assignments:*")
            logger.info(f"[Cache] Invalidated all agent caches after rebalance")
        
        return result
    
    # === Delegate all other methods to base repository ===
    
    def __getattr__(self, name):
        """Delegate any unimplemented methods to base repository"""
        return getattr(self.base_repo, name)