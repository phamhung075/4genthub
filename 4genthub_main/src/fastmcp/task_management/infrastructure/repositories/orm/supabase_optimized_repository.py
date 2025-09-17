"""
Supabase-Optimized Task Repository

Special optimizations for Supabase cloud database to minimize latency:
- Minimal queries without eager loading
- Single query operations
- Deferred relationship loading
- Optimized for network latency
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, desc, text
from sqlalchemy.orm import Session, noload

from .task_repository import ORMTaskRepository
from ...database.models import Task
from ....domain.entities.task import Task as TaskEntity

logger = logging.getLogger(__name__)


class SupabaseOptimizedRepository(ORMTaskRepository):
    """Repository optimized specifically for Supabase cloud database"""
    
    def __init__(self, git_branch_id: str = None):
        """Initialize Supabase-optimized repository"""
        # Fix: Pass git_branch_id as keyword argument, not positional
        super().__init__(session=None, git_branch_id=git_branch_id)
        logger.info(f"Using Supabase-optimized repository for minimal latency, git_branch_id: {self.git_branch_id}")
    
    def list_tasks_minimal(self, status: str = None, priority: str = None,
                          assignee_id: str = None, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get minimal task data in a single query - no relationships loaded.
        Optimized for Supabase cloud latency.
        
        Returns raw dictionaries instead of entities for speed.
        """
        # Handle None parameters with defaults
        if limit is None:
            limit = 20
        if offset is None:
            offset = 0
            
        # Validate parameters
        if limit < 0:
            limit = 20
            logger.warning("Invalid limit, using default: 20")
        if offset < 0:
            offset = 0
            logger.warning("Invalid offset, using default: 0")
        if limit > 1000:
            limit = 1000
            logger.warning("Limit too large, capping at 1000")
        
        # Type validation for status and priority
        if status is not None and not isinstance(status, str):
            logger.warning(f"Invalid status type: {type(status)}, ignoring")
            status = None
        if priority is not None and not isinstance(priority, str):
            logger.warning(f"Invalid priority type: {type(priority)}, ignoring")
            priority = None
            
        with self.get_db_session() as session:
            # Use raw SQL for maximum performance with Supabase
            filters = ["1=1"]  # Always true base condition
            params = {"limit": limit, "offset": offset}
            
            if self.git_branch_id:
                filters.append("git_branch_id = :git_branch_id")
                params["git_branch_id"] = self.git_branch_id
            
            if status:
                filters.append("status = :status")
                params["status"] = status
            
            if priority:
                filters.append("priority = :priority")
                params["priority"] = priority
            
            if assignee_id:
                filters.append("EXISTS (SELECT 1 FROM task_assignees WHERE task_id = tasks.id AND assignee_id = :assignee_id)")
                params["assignee_id"] = assignee_id
            
            # Single optimized query - no joins, no eager loading
            sql = text(f"""
                SELECT 
                    id,
                    title,
                    status,
                    priority,
                    created_at,
                    updated_at,
                    -- Count relationships in subqueries (single round trip)
                    (SELECT COUNT(*) FROM subtasks WHERE task_id = tasks.id) as subtask_count,
                    (SELECT COUNT(*) FROM task_assignees WHERE task_id = tasks.id) as assignee_count,
                    (SELECT COUNT(*) FROM task_dependencies WHERE task_id = tasks.id) as dependency_count
                FROM tasks
                WHERE {' AND '.join(filters)}
                ORDER BY created_at DESC
                LIMIT :limit
                OFFSET :offset
            """)
            
            result = session.execute(sql, params)
            tasks = []
            
            for row in result:
                tasks.append({
                    "id": row.id,
                    "title": row.title,
                    "status": row.status,
                    "priority": row.priority,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "subtask_count": row.subtask_count,
                    "assignee_count": row.assignee_count,
                    "dependency_count": row.dependency_count,
                    "has_relationships": (row.subtask_count + row.assignee_count + row.dependency_count) > 0
                })
            
            logger.info(f"Fetched {len(tasks)} tasks with minimal query (Supabase optimized)")
            return tasks
    
    def list_tasks_no_relations(self, status: str = None, priority: str = None,
                               assignee_id: str = None, limit: int = 50,
                               offset: int = 0) -> List[TaskEntity]:
        """
        List tasks without loading any relationships.
        Uses noload to explicitly prevent relationship queries.
        """
        with self.get_db_session() as session:
            # Build query with explicit noload for all relationships
            query = session.query(Task).options(
                noload(Task.assignees),
                noload(Task.labels),
                noload(Task.subtasks),
                noload(Task.dependencies)
            )
            
            # Apply filters
            filters = []
            if self.git_branch_id:
                filters.append(Task.git_branch_id == self.git_branch_id)
            if status:
                filters.append(Task.status == status)
            if priority:
                filters.append(Task.priority == priority)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Apply ordering and pagination
            query = query.order_by(desc(Task.created_at))
            query = query.offset(offset).limit(limit)
            
            # Execute query
            tasks = query.all()
            
            # Convert to entities with empty relationships
            entities = []
            for task in tasks:
                entity = self._model_to_entity_minimal(task)
                entities.append(entity)
            
            logger.info(f"Fetched {len(entities)} tasks without relationships (Supabase optimized)")
            return entities
    
    def _model_to_entity_minimal(self, task_model: Task) -> TaskEntity:
        """Convert model to entity without loading relationships"""
        return TaskEntity(
            id=task_model.id,
            title=task_model.title,
            description=task_model.description or "",
            status=task_model.status,
            priority=task_model.priority,
            subtasks=[],  # Empty - not loaded
            assignees=[],  # Empty - not loaded  
            dependencies=[],  # Empty - not loaded
            labels=[],  # Empty - not loaded
            created_at=task_model.created_at,
            updated_at=task_model.updated_at,
            git_branch_id=task_model.git_branch_id,
            context_id=task_model.context_id,
            details=task_model.details,
            estimated_effort=task_model.estimated_effort,
            due_date=task_model.due_date
        )
    
    def get_task_with_counts(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single task with relationship counts only.
        Single query with subqueries for counts.
        """
        # Validate UUID format
        try:
            import uuid
            uuid.UUID(task_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid task UUID: {task_id}")
            return None
            
        with self.get_db_session() as session:
            sql = text("""
                SELECT 
                    t.*,
                    (SELECT COUNT(*) FROM subtasks WHERE task_id = t.id) as subtask_count,
                    (SELECT COUNT(*) FROM task_assignees WHERE task_id = t.id) as assignee_count,
                    (SELECT COUNT(*) FROM task_dependencies WHERE task_id = t.id) as dependency_count,
                    (SELECT COUNT(*) FROM task_labels WHERE task_id = t.id) as label_count
                FROM tasks t
                WHERE t.id = :task_id
            """)
            
            result = session.execute(sql, {"task_id": task_id}).first()
            
            if not result:
                return None
            
            return {
                "id": result.id,
                "title": result.title,
                "description": result.description,
                "status": result.status,
                "priority": result.priority,
                "created_at": result.created_at.isoformat() if result.created_at else None,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                "subtask_count": result.subtask_count,
                "assignee_count": result.assignee_count,
                "dependency_count": result.dependency_count,
                "label_count": result.label_count,
                "git_branch_id": result.git_branch_id,
                "context_id": result.context_id,
                "details": result.details,
                "estimated_effort": result.estimated_effort,
                "due_date": result.due_date if result.due_date else None
            }