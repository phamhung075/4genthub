"""Optimized Task Repository with Performance Enhancements

This module provides an optimized version of the task repository with:
- Query optimization
- Result caching
- Pagination improvements
- Reduced payload sizes
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import selectinload, contains_eager

from .task_repository import ORMTaskRepository
from ...database.models import Task, TaskAssignee, TaskLabel, Label
from ....domain.entities.task import Task as TaskEntity
from ...performance.task_performance_optimizer import get_performance_optimizer

logger = logging.getLogger(__name__)


class OptimizedTaskRepository(ORMTaskRepository):
    """Optimized task repository with performance enhancements"""
    
    def __init__(self, git_branch_id: str = None):
        """Initialize optimized task repository
        
        Args:
            git_branch_id: Optional branch ID filter
        """
        logger.debug(f"[OPTIMIZED_REPO] Initializing with git_branch_id: {git_branch_id}")
        # Fix: Pass git_branch_id as keyword argument, not positional
        super().__init__(session=None, git_branch_id=git_branch_id)
        self.optimizer = get_performance_optimizer()
        logger.debug(f"[OPTIMIZED_REPO] After init, self.git_branch_id: {self.git_branch_id}")
    
    def list_tasks(self, status: str | None = None, priority: str | None = None,
                  assignee_id: str | None = None, limit: int = 100,
                  offset: int = 0, use_cache: bool = True) -> list[TaskEntity]:
        """List tasks with optimized query and caching
        
        Args:
            status: Optional status filter
            priority: Optional priority filter
            assignee_id: Optional assignee filter
            limit: Maximum number of results
            offset: Result offset for pagination
            use_cache: Whether to use cache
            
        Returns:
            List of task entities
        """
        # Generate cache key
        cache_key = self.optimizer.get_cache_key(
            'list_tasks',
            git_branch_id=self.git_branch_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            limit=limit,
            offset=offset
        )
        
        # Check cache if enabled
        if use_cache:
            cached_result = self.optimizer.get_from_cache(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached task list (key: {cache_key})")
                return cached_result
        
        with self.get_db_session() as session:
            # Build optimized query using selectinload instead of joinedload
            # This prevents duplicate rows and is more efficient for collections
            query = session.query(Task).options(
                selectinload(Task.assignees),
                selectinload(Task.labels).selectinload(TaskLabel.label),
                selectinload(Task.subtasks),
                selectinload(Task.dependencies)
            )
            
            # Apply filters
            filters = []
            logger.debug(f"[OPTIMIZED_REPO] list_tasks_minimal - self.git_branch_id: {self.git_branch_id}")
            if self.git_branch_id:
                filters.append(Task.git_branch_id == self.git_branch_id)
                logger.debug(f"[OPTIMIZED_REPO] Applied git_branch_id filter: {self.git_branch_id}")
            else:
                logger.debug(f"[OPTIMIZED_REPO] NO git_branch_id filter - returning ALL tasks")
            if status:
                filters.append(Task.status == status)
            if priority:
                filters.append(Task.priority == priority)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Filter by assignee if specified
            if assignee_id:
                # Use exists subquery instead of join for better performance
                query = query.filter(
                    Task.assignees.any(TaskAssignee.assignee_id == assignee_id)
                )
            
            # Apply ordering and pagination
            query = query.order_by(desc(Task.created_at))
            query = query.offset(offset).limit(limit)
            
            # Execute query with optimization hints
            query = self.optimizer.optimize_task_query(session, query, {
                'status': status,
                'priority': priority,
                'assignee_id': assignee_id
            })
            
            tasks = query.all()
            result = [self._model_to_entity(task) for task in tasks]
            
            # Cache the result
            if use_cache:
                self.optimizer.set_cache(cache_key, result)
                logger.info(f"Cached task list (key: {cache_key})")
            
            return result
    
    def list_tasks_minimal(self, status: str | None = None, priority: str | None = None,
                           assignee_id: str | None = None, limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """List tasks with minimal data for improved performance
        
        Args:
            status: Optional status filter
            priority: Optional priority filter
            assignee_id: Optional assignee filter
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of minimal task data dictionaries
        """
        # Generate cache key
        cache_key = self.optimizer.get_cache_key(
            'list_tasks_minimal',
            git_branch_id=self.git_branch_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            limit=limit,
            offset=offset
        )
        
        # Check cache
        cached_result = self.optimizer.get_from_cache(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached minimal task list (key: {cache_key})")
            return cached_result
        
        with self.get_db_session() as session:
            # Query only essential fields for list view
            query = session.query(
                Task.id,
                Task.title,
                Task.status,
                Task.priority,
                Task.progress_percentage,
                Task.due_date,
                Task.updated_at,
                func.count(TaskAssignee.id).label('assignees_count')
            ).outerjoin(TaskAssignee)
            
            # Apply filters
            filters = []
            logger.debug(f"[OPTIMIZED_REPO] list_tasks_minimal - self.git_branch_id: {self.git_branch_id}")
            if self.git_branch_id:
                filters.append(Task.git_branch_id == self.git_branch_id)
                logger.debug(f"[OPTIMIZED_REPO] Applied git_branch_id filter: {self.git_branch_id}")
            else:
                logger.debug(f"[OPTIMIZED_REPO] NO git_branch_id filter - returning ALL tasks")
            if status:
                filters.append(Task.status == status)
            if priority:
                filters.append(Task.priority == priority)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Filter by assignee if specified
            if assignee_id:
                query = query.filter(TaskAssignee.assignee_id == assignee_id)
            
            # Group by task fields
            query = query.group_by(
                Task.id,
                Task.title,
                Task.status,
                Task.priority,
                Task.progress_percentage,
                Task.due_date,
                Task.updated_at
            )
            
            # Apply ordering and pagination
            query = query.order_by(desc(Task.updated_at))
            query = query.offset(offset).limit(limit)
            
            results = query.all()
            
            # Get labels separately (more efficient than join)
            task_ids = [r.id for r in results]
            if task_ids:
                labels_query = session.query(
                    TaskLabel.task_id,
                    Label.name
                ).join(Label).filter(TaskLabel.task_id.in_(task_ids))
                
                labels_by_task = {}
                for task_id, label_name in labels_query:
                    if task_id not in labels_by_task:
                        labels_by_task[task_id] = []
                    labels_by_task[task_id].append(label_name)
            else:
                labels_by_task = {}
            
            # Build minimal response
            minimal_tasks = []
            for r in results:
                minimal_tasks.append({
                    'id': r.id,
                    'title': r.title,
                    'status': r.status,
                    'priority': r.priority,
                    'progress_percentage': r.progress_percentage,
                    'assignees_count': r.assignees_count,
                    'labels': labels_by_task.get(r.id, []),
                    'due_date': r.due_date,
                    'updated_at': r.updated_at.isoformat() if r.updated_at else None
                })
            
            # Cache the result
            self.optimizer.set_cache(cache_key, minimal_tasks)
            logger.info(f"Cached minimal task list (key: {cache_key})")
            
            return minimal_tasks
    
    def get_task_count(self, status: str | None = None, use_cache: bool = True) -> int:
        """Get count of tasks with caching
        
        Args:
            status: Optional status filter
            use_cache: Whether to use cache
            
        Returns:
            Count of tasks
        """
        # Generate cache key
        cache_key = self.optimizer.get_cache_key(
            'task_count',
            git_branch_id=self.git_branch_id,
            status=status
        )
        
        # Check cache if enabled
        if use_cache:
            cached_result = self.optimizer.get_from_cache(cache_key)
            if cached_result is not None:
                logger.info(f"Returning cached task count (key: {cache_key})")
                return cached_result
        
        with self.get_db_session() as session:
            query = session.query(func.count(Task.id))
            
            # Apply filters
            filters = []
            if self.git_branch_id:
                filters.append(Task.git_branch_id == self.git_branch_id)
            if status:
                filters.append(Task.status == status)
            
            if filters:
                query = query.filter(and_(*filters))
            
            count = query.scalar()
            
            # Cache the result
            if use_cache:
                self.optimizer.set_cache(cache_key, count)
                logger.info(f"Cached task count (key: {cache_key})")
            
            return count
    
    def search_tasks(self, query: str, limit: int = 50) -> list[TaskEntity]:
        """Search tasks with optimized query
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching task entities
        """
        # Generate cache key
        cache_key = self.optimizer.get_cache_key(
            'search_tasks',
            git_branch_id=self.git_branch_id,
            query=query,
            limit=limit
        )
        
        # Check cache
        cached_result = self.optimizer.get_from_cache(cache_key)
        if cached_result is not None:
            logger.info(f"Returning cached search results (key: {cache_key})")
            return cached_result
        
        # Use parent implementation with caching
        result = super().search_tasks(query, limit)
        
        # Cache the result
        self.optimizer.set_cache(cache_key, result)
        logger.info(f"Cached search results (key: {cache_key})")
        
        return result
    
    def invalidate_cache(self, operation: str = None) -> None:
        """Invalidate cache entries
        
        Args:
            operation: Optional operation to invalidate (None = all)
        """
        if operation:
            # Invalidate specific operation cache
            keys_to_remove = [
                key for key in self.optimizer._cache.keys()
                if operation in key
            ]
            for key in keys_to_remove:
                del self.optimizer._cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for operation: {operation}")
        else:
            # Clear all cache
            self.optimizer._cache.clear()
            logger.info("Cleared all cache entries")
    
    def create_task(self, task: TaskEntity) -> TaskEntity:
        """Create task and invalidate relevant cache
        
        Args:
            task: Task entity to create
            
        Returns:
            Created task entity
        """
        result = super().create_task(task)
        
        # Invalidate list and count caches
        self.invalidate_cache('list_tasks')
        self.invalidate_cache('task_count')
        
        return result
    
    def update_task(self, task_id: str, **updates) -> TaskEntity:
        """Update task and invalidate relevant cache
        
        Args:
            task_id: Task ID
            **updates: Fields to update
            
        Returns:
            Updated task entity
        """
        result = super().update_task(task_id, **updates)
        
        # Invalidate caches
        self.invalidate_cache('list_tasks')
        self.invalidate_cache('search_tasks')
        
        return result
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task and invalidate relevant cache
        
        Args:
            task_id: Task ID
            
        Returns:
            True if deleted successfully
        """
        result = super().delete_task(task_id)
        
        if result:
            # Invalidate caches
            self.invalidate_cache('list_tasks')
            self.invalidate_cache('task_count')
            self.invalidate_cache('search_tasks')
        
        return result