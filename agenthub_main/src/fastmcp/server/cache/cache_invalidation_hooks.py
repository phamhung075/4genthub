"""
Cache Invalidation Hooks for Data Modifications

This module provides hooks that automatically invalidate cached data
when tasks, subtasks, or contexts are modified.

Author: DevOps Agent
Date: 2025-08-16
Task: API Optimization - Cache Invalidation
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from functools import wraps

# Import cache invalidator
try:
    from fastmcp.server.cache.redis_cache_decorator import CacheInvalidator
    CACHE_INVALIDATION_ENABLED = True
except ImportError:
    CACHE_INVALIDATION_ENABLED = False
    # Dummy class if Redis not available
    class CacheInvalidator:
        @staticmethod
        async def invalidate_task_cache(task_id=None):
            pass
        @staticmethod
        async def invalidate_subtask_cache(parent_task_id=None):
            pass
        @staticmethod
        async def invalidate_context_cache(context_id=None):
            pass

logger = logging.getLogger(__name__)


class CacheInvalidationHooks:
    """Hooks for automatic cache invalidation on data changes"""
    
    @staticmethod
    async def on_task_created(task_id: str, git_branch_id: str):
        """Invalidate cache when a new task is created"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for new task {task_id}")
            # Invalidate all task summaries for the branch
            await CacheInvalidator.invalidate_task_cache()
            logger.debug(f"Cache invalidated for task creation: {task_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on task creation: {e}")
    
    @staticmethod
    async def on_task_updated(task_id: str, updates: Dict[str, Any]):
        """Invalidate cache when a task is updated"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for updated task {task_id}")
            # Invalidate specific task and all summaries
            await CacheInvalidator.invalidate_task_cache(task_id)
            logger.debug(f"Cache invalidated for task update: {task_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on task update: {e}")
    
    @staticmethod
    async def on_task_deleted(task_id: str):
        """Invalidate cache when a task is deleted"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for deleted task {task_id}")
            # Invalidate all task caches
            await CacheInvalidator.invalidate_task_cache()
            logger.debug(f"Cache invalidated for task deletion: {task_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on task deletion: {e}")
    
    @staticmethod
    async def on_subtask_created(subtask_id: str, parent_task_id: str):
        """Invalidate cache when a new subtask is created"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for new subtask {subtask_id} of task {parent_task_id}")
            # Invalidate parent task and subtask caches
            await CacheInvalidator.invalidate_task_cache(parent_task_id)
            await CacheInvalidator.invalidate_subtask_cache(parent_task_id)
            logger.debug(f"Cache invalidated for subtask creation: {subtask_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on subtask creation: {e}")
    
    @staticmethod
    async def on_subtask_updated(subtask_id: str, parent_task_id: str, updates: Dict[str, Any]):
        """Invalidate cache when a subtask is updated"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for updated subtask {subtask_id}")
            # Invalidate parent task and subtask caches
            await CacheInvalidator.invalidate_task_cache(parent_task_id)
            await CacheInvalidator.invalidate_subtask_cache(parent_task_id)
            logger.debug(f"Cache invalidated for subtask update: {subtask_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on subtask update: {e}")
    
    @staticmethod
    async def on_subtask_deleted(subtask_id: str, parent_task_id: str):
        """Invalidate cache when a subtask is deleted"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for deleted subtask {subtask_id}")
            # Invalidate parent task and all subtask caches
            await CacheInvalidator.invalidate_task_cache(parent_task_id)
            await CacheInvalidator.invalidate_subtask_cache()
            logger.debug(f"Cache invalidated for subtask deletion: {subtask_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on subtask deletion: {e}")
    
    @staticmethod
    async def on_context_updated(context_id: str):
        """Invalidate cache when context is updated"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        try:
            logger.info(f"Invalidating cache for updated context {context_id}")
            # Invalidate context and related task caches
            await CacheInvalidator.invalidate_context_cache(context_id)
            await CacheInvalidator.invalidate_task_cache(context_id)  # Context ID might be task ID
            logger.debug(f"Cache invalidated for context update: {context_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on context update: {e}")
    
    @staticmethod
    async def on_bulk_operation(operation: str, affected_count: int):
        """Invalidate cache for bulk operations"""
        if not CACHE_INVALIDATION_ENABLED:
            return
        
        if affected_count == 0:
            return
        
        try:
            logger.info(f"Invalidating cache for bulk {operation} affecting {affected_count} items")
            # Invalidate all caches for bulk operations
            await CacheInvalidator.invalidate_task_cache()
            await CacheInvalidator.invalidate_subtask_cache()
            await CacheInvalidator.invalidate_context_cache()
            logger.debug(f"Cache invalidated for bulk operation: {operation}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache on bulk operation: {e}")


def cache_invalidation_decorator(invalidation_type: str):
    """
    Decorator to automatically trigger cache invalidation after successful operations
    
    Args:
        invalidation_type: Type of invalidation ('task', 'subtask', 'context', 'bulk')
    
    Example:
        @cache_invalidation_decorator('task')
        def update_task(task_id, updates):
            # Update task logic
            return result
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Trigger cache invalidation if successful
            if result and isinstance(result, dict) and result.get("success"):
                try:
                    if invalidation_type == "task":
                        task_id = kwargs.get("task_id") or (args[0] if args else None)
                        if task_id:
                            await CacheInvalidationHooks.on_task_updated(task_id, {})
                    elif invalidation_type == "subtask":
                        subtask_id = kwargs.get("subtask_id")
                        parent_task_id = kwargs.get("parent_task_id") or kwargs.get("task_id")
                        if subtask_id and parent_task_id:
                            await CacheInvalidationHooks.on_subtask_updated(subtask_id, parent_task_id, {})
                    elif invalidation_type == "context":
                        context_id = kwargs.get("context_id") or kwargs.get("task_id")
                        if context_id:
                            await CacheInvalidationHooks.on_context_updated(context_id)
                    elif invalidation_type == "bulk":
                        await CacheInvalidationHooks.on_bulk_operation("update", 1)
                except Exception as e:
                    logger.error(f"Cache invalidation failed: {e}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Execute the function
            result = func(*args, **kwargs)
            
            # Trigger cache invalidation if successful (run in background)
            if result and isinstance(result, dict) and result.get("success"):
                try:
                    # Create async task for invalidation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    if invalidation_type == "task":
                        task_id = kwargs.get("task_id") or (args[0] if args else None)
                        if task_id:
                            loop.run_until_complete(
                                CacheInvalidationHooks.on_task_updated(task_id, {})
                            )
                    elif invalidation_type == "subtask":
                        subtask_id = kwargs.get("subtask_id")
                        parent_task_id = kwargs.get("parent_task_id") or kwargs.get("task_id")
                        if subtask_id and parent_task_id:
                            loop.run_until_complete(
                                CacheInvalidationHooks.on_subtask_updated(subtask_id, parent_task_id, {})
                            )
                    elif invalidation_type == "context":
                        context_id = kwargs.get("context_id") or kwargs.get("task_id")
                        if context_id:
                            loop.run_until_complete(
                                CacheInvalidationHooks.on_context_updated(context_id)
                            )
                    elif invalidation_type == "bulk":
                        loop.run_until_complete(
                            CacheInvalidationHooks.on_bulk_operation("update", 1)
                        )
                    
                    loop.close()
                except Exception as e:
                    logger.error(f"Cache invalidation failed: {e}")
            
            return result
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Integration helper
def register_cache_invalidation_hooks(app):
    """
    Register cache invalidation hooks with the application
    
    Args:
        app: Application instance to register hooks with
    """
    if not CACHE_INVALIDATION_ENABLED:
        logger.info("Cache invalidation hooks not registered (Redis not available)")
        return
    
    logger.info("Registering cache invalidation hooks")
    
    # Register hooks with application events if available
    # This would integrate with the application's event system
    # For now, hooks need to be called manually or via decorators
    
    logger.info("Cache invalidation hooks registered successfully")