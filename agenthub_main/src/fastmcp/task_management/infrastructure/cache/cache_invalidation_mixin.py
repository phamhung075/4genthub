"""
Cache Invalidation Mixin for Repositories

Provides a reusable mixin that adds cache invalidation capabilities
to repository classes for consistent cache management.
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class CacheOperation(Enum):
    """Types of cache operations"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class CacheInvalidationMixin:
    """
    Mixin to add cache invalidation capabilities to repositories.
    
    Usage:
        class MyRepository(CacheInvalidationMixin, BaseRepository):
            def update(self, entity_id: str, data: dict):
                result = super().update(entity_id, data)
                self.invalidate_cache_for_entity(
                    entity_type="context",
                    entity_id=entity_id,
                    operation=CacheOperation.UPDATE,
                    user_id=self.user_id
                )
                return result
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize mixin"""
        super().__init__(*args, **kwargs)
        self._cache = None
        self._cache_enabled = True
    
    @property
    def cache(self):
        """Lazy load cache instance"""
        if self._cache is None and self._cache_enabled:
            try:
                from .context_cache import get_context_cache
                self._cache = get_context_cache()
            except Exception as e:
                logger.warning(f"Cache not available: {e}")
                self._cache_enabled = False
        return self._cache
    
    def invalidate_cache_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        operation: CacheOperation,
        user_id: Optional[str] = None,
        level: Optional[str] = None,
        propagate: bool = True
    ):
        """
        Invalidate cache for a specific entity.
        
        Args:
            entity_type: Type of entity (context, task, etc.)
            entity_id: Entity identifier
            operation: Type of operation performed
            user_id: User ID for user-scoped caches
            level: Context level (global, project, branch, task)
            propagate: Whether to propagate invalidation to related caches
        """
        if not self.cache:
            return
        
        try:
            # Determine user_id
            if not user_id:
                user_id = getattr(self, 'user_id', None)
            
            if not user_id:
                logger.warning(f"No user_id available for cache invalidation of {entity_type}:{entity_id}")
                return
            
            # Invalidate based on entity type
            if entity_type == "context":
                self._invalidate_context_cache(entity_id, level, user_id, operation, propagate)
            elif entity_type == "task":
                self._invalidate_task_cache(entity_id, user_id, operation, propagate)
            elif entity_type == "project":
                self._invalidate_project_cache(entity_id, user_id, operation, propagate)
            elif entity_type == "branch":
                self._invalidate_branch_cache(entity_id, user_id, operation, propagate)
            else:
                logger.warning(f"Unknown entity type for cache invalidation: {entity_type}")
            
            logger.debug(f"Cache invalidated for {entity_type}:{entity_id} after {operation.value}")
            
        except Exception as e:
            # Don't let cache errors break the main operation
            logger.error(f"Error invalidating cache for {entity_type}:{entity_id}: {e}")
    
    def _invalidate_context_cache(
        self,
        context_id: str,
        level: Optional[str],
        user_id: str,
        operation: CacheOperation,
        propagate: bool
    ):
        """Invalidate context-specific caches"""
        if not level:
            logger.warning(f"No level specified for context cache invalidation: {context_id}")
            return
        
        # Invalidate the specific context
        self.cache.invalidate_context(
            user_id=user_id,
            level=level,
            context_id=context_id
        )
        
        # Invalidate inheritance chain
        self.cache.invalidate_inheritance(
            user_id=user_id,
            level=level,
            context_id=context_id
        )
        
        # Propagate invalidation if needed
        if propagate and operation != CacheOperation.DELETE:
            self._propagate_context_invalidation(level, context_id, user_id)
    
    def _invalidate_task_cache(
        self,
        task_id: str,
        user_id: str,
        operation: CacheOperation,
        propagate: bool
    ):
        """Invalidate task-related caches"""
        # Tasks might have associated contexts
        self.cache.invalidate_context(
            user_id=user_id,
            level="task",
            context_id=task_id
        )
        
        if propagate and operation == CacheOperation.DELETE:
            # If task is deleted, invalidate branch context it belonged to
            # This would need task metadata to know the branch
            pass
    
    def _invalidate_project_cache(
        self,
        project_id: str,
        user_id: str,
        operation: CacheOperation,
        propagate: bool
    ):
        """Invalidate project-related caches"""
        self.cache.invalidate_context(
            user_id=user_id,
            level="project",
            context_id=project_id
        )
        
        if propagate:
            # Project changes might affect branch and task contexts
            self._invalidate_child_contexts("project", project_id, user_id)
    
    def _invalidate_branch_cache(
        self,
        branch_id: str,
        user_id: str,
        operation: CacheOperation,
        propagate: bool
    ):
        """Invalidate branch-related caches"""
        self.cache.invalidate_context(
            user_id=user_id,
            level="branch",
            context_id=branch_id
        )
        
        if propagate:
            # Branch changes might affect task contexts
            self._invalidate_child_contexts("branch", branch_id, user_id)
    
    def _propagate_context_invalidation(
        self,
        level: str,
        context_id: str,
        user_id: str
    ):
        """Propagate cache invalidation to related contexts"""
        
        # Define propagation rules
        propagation_rules = {
            "global": ["project", "branch", "task"],  # Global affects all
            "project": ["branch", "task"],            # Project affects branches and tasks
            "branch": ["task"],                        # Branch affects tasks
            "task": []                                 # Task doesn't propagate
        }
        
        affected_levels = propagation_rules.get(level, [])
        
        if affected_levels:
            logger.debug(f"Propagating cache invalidation from {level}:{context_id} to {affected_levels}")
            
            # For complete invalidation, we'd need to query for all affected contexts
            # For now, we'll invalidate all contexts at affected levels for the user
            for affected_level in affected_levels:
                self.cache.invalidate_context(
                    user_id=user_id,
                    level=affected_level
                )
                self.cache.invalidate_inheritance(
                    user_id=user_id,
                    level=affected_level
                )
    
    def _invalidate_child_contexts(
        self,
        parent_level: str,
        parent_id: str,
        user_id: str
    ):
        """Invalidate child contexts when parent changes"""
        # This is a simplified version - in reality, we'd query for specific children
        # For now, invalidate all contexts at child levels
        
        if parent_level == "global":
            # Invalidate all user contexts
            self.cache.invalidate_context(user_id=user_id)
            self.cache.invalidate_inheritance(user_id=user_id)
        elif parent_level == "project":
            # Invalidate branch and task contexts
            self.cache.invalidate_context(user_id=user_id, level="branch")
            self.cache.invalidate_context(user_id=user_id, level="task")
            self.cache.invalidate_inheritance(user_id=user_id, level="branch")
            self.cache.invalidate_inheritance(user_id=user_id, level="task")
        elif parent_level == "branch":
            # Invalidate task contexts
            self.cache.invalidate_context(user_id=user_id, level="task")
            self.cache.invalidate_inheritance(user_id=user_id, level="task")
    
    def invalidate_bulk(
        self,
        entity_type: str,
        entity_ids: List[str],
        operation: CacheOperation,
        user_id: Optional[str] = None,
        level: Optional[str] = None
    ):
        """
        Invalidate cache for multiple entities.
        
        Args:
            entity_type: Type of entities
            entity_ids: List of entity identifiers
            operation: Type of operation performed
            user_id: User ID for user-scoped caches
            level: Context level (for context entities)
        """
        for entity_id in entity_ids:
            self.invalidate_cache_for_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                operation=operation,
                user_id=user_id,
                level=level,
                propagate=False  # Don't propagate for bulk operations
            )
        
        # Do one propagation at the end if needed
        if entity_ids and level:
            if not user_id:
                user_id = getattr(self, 'user_id', None)
            if user_id:
                self._propagate_context_invalidation(level, entity_ids[0], user_id)
    
    def invalidate_all_user_cache(self, user_id: Optional[str] = None):
        """
        Invalidate all caches for a user.
        
        Args:
            user_id: User ID (uses instance user_id if not provided)
        """
        if not self.cache:
            return
        
        if not user_id:
            user_id = getattr(self, 'user_id', None)
        
        if not user_id:
            logger.warning("No user_id available for complete cache invalidation")
            return
        
        try:
            # Invalidate all context and inheritance caches for the user
            self.cache.invalidate_context(user_id=user_id)
            self.cache.invalidate_inheritance(user_id=user_id)
            logger.info(f"All caches invalidated for user: {user_id}")
        except Exception as e:
            logger.error(f"Error invalidating all caches for user {user_id}: {e}")
    
    def warm_cache(
        self,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        level: Optional[str] = None,
        ttl: Optional[int] = None
    ):
        """
        Warm cache with new data after updates.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            data: Data to cache
            user_id: User ID for user-scoped caches
            level: Context level (for context entities)
            ttl: Time-to-live in seconds
        """
        if not self.cache:
            return
        
        if not user_id:
            user_id = getattr(self, 'user_id', None)
        
        if not user_id:
            return
        
        try:
            if entity_type == "context" and level:
                self.cache.set_context(
                    level=level,
                    context_id=entity_id,
                    user_id=user_id,
                    data=data,
                    ttl=ttl
                )
                logger.debug(f"Cache warmed for {entity_type}:{entity_id}")
        except Exception as e:
            logger.error(f"Error warming cache for {entity_type}:{entity_id}: {e}")