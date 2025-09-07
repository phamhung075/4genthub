"""
ORM Subtask Repository Implementation using SQLAlchemy

This module provides the ORM implementation of the SubtaskRepository
interface using SQLAlchemy for database abstraction.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...database.models import TaskSubtask
from ...database.database_config import get_session
from ..base_orm_repository import BaseORMRepository
from ..base_user_scoped_repository import BaseUserScopedRepository
from ....domain.entities.subtask import Subtask
from ....domain.repositories.subtask_repository import SubtaskRepository
from ....domain.value_objects.task_id import TaskId
from ....domain.value_objects.subtask_id import SubtaskId
from ....domain.value_objects.task_status import TaskStatus
from ....domain.value_objects.priority import Priority
from ....domain.exceptions.base_exceptions import (
    DatabaseException,
    ResourceNotFoundException,
    ValidationException
)

logger = logging.getLogger(__name__)


class ORMSubtaskRepository(BaseORMRepository[TaskSubtask], BaseUserScopedRepository, SubtaskRepository):
    """
    ORM implementation of SubtaskRepository using SQLAlchemy.
    
    Provides database operations for subtasks with proper data transformation
    between domain objects and ORM models.
    """
    
    def __init__(self, session=None, user_id: Optional[str] = None):
        """Initialize the ORM subtask repository with user isolation."""
        BaseORMRepository.__init__(self, TaskSubtask)
        BaseUserScopedRepository.__init__(self, session or self.get_db_session(), user_id)
    
    def save(self, subtask: Subtask) -> bool:
        """
        Save a subtask to the database.
        
        Args:
            subtask: Subtask domain entity
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with self.get_db_session() as session:
                # Convert domain entity to ORM model data
                model_data = self._to_model_data(subtask)
                
                if subtask.id:
                    # Update existing subtask
                    existing = session.query(TaskSubtask).filter(
                        TaskSubtask.id == subtask.id.value
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in model_data.items():
                            if key != 'id':  # Don't update primary key
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now(timezone.utc)
                        session.flush()
                        
                        # Update the domain entity with the persisted data
                        subtask.updated_at = existing.updated_at
                        return True
                    else:
                        # ID provided but doesn't exist, create new
                        model_data['id'] = subtask.id.value
                else:
                    # Generate new ID if not provided
                    if not subtask.id:
                        new_id = self.get_next_id(subtask.parent_task_id)
                        subtask.id = new_id
                        model_data['id'] = new_id.value
                
                # Create new subtask
                new_subtask = TaskSubtask(**model_data)
                session.add(new_subtask)
                session.flush()
                session.refresh(new_subtask)
                
                # Update domain entity with persisted timestamps
                subtask.created_at = new_subtask.created_at
                subtask.updated_at = new_subtask.updated_at
                
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to save subtask: {e}")
            raise DatabaseException(
                message=f"Failed to save subtask: {str(e)}",
                operation="save_subtask",
                table="task_subtasks"
            )
        except Exception as e:
            logger.error(f"Unexpected error saving subtask: {e}")
            return False
    
    def find_by_id(self, id: str) -> Optional[Subtask]:
        """
        Find a subtask by its ID.
        
        Args:
            id: Subtask ID string
            
        Returns:
            Subtask domain entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                model = session.query(TaskSubtask).filter(
                    TaskSubtask.id == id
                ).first()
                
                if model:
                    return self._to_domain_entity(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtask by id {id}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtask by id: {str(e)}",
                operation="find_by_id",
                table="task_subtasks"
            )
    
    def find_by_parent_task_id(self, parent_task_id: TaskId) -> List[Subtask]:
        """
        Find all subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(TaskSubtask).filter(
                    TaskSubtask.task_id == parent_task_id.value
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(TaskSubtask.created_at.asc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks for task: {str(e)}",
                operation="find_by_parent_task_id",
                table="task_subtasks"
            )
    
    def find_by_assignee(self, assignee: str) -> List[Subtask]:
        """
        Find subtasks by assignee.
        
        Args:
            assignee: Assignee name/ID
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                # Use JSON operations to search within assignees array
                query = session.query(TaskSubtask).filter(
                    TaskSubtask.assignees.contains([assignee])
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(TaskSubtask.created_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks by assignee {assignee}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks by assignee: {str(e)}",
                operation="find_by_assignee",
                table="task_subtasks"
            )
    
    def find_by_status(self, status: str) -> List[Subtask]:
        """
        Find subtasks by status.
        
        Args:
            status: Status string
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(TaskSubtask).filter(
                    TaskSubtask.status == status
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(TaskSubtask.created_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks by status {status}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks by status: {str(e)}",
                operation="find_by_status",
                table="task_subtasks"
            )
    
    def find_completed(self, parent_task_id: TaskId) -> List[Subtask]:
        """
        Find completed subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of completed subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status == 'done'
                    )
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(TaskSubtask.completed_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find completed subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find completed subtasks: {str(e)}",
                operation="find_completed",
                table="task_subtasks"
            )
    
    def find_pending(self, parent_task_id: TaskId) -> List[Subtask]:
        """
        Find pending subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of pending subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status.in_(['todo', 'in_progress', 'blocked'])
                    )
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(TaskSubtask.created_at.asc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find pending subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find pending subtasks: {str(e)}",
                operation="find_pending",
                table="task_subtasks"
            )
    
    def delete(self, id: str) -> bool:
        """
        Delete a subtask by its ID.
        
        Args:
            id: Subtask ID string
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            with self.get_db_session() as session:
                result = session.query(TaskSubtask).filter(
                    TaskSubtask.id == id
                ).delete()
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete subtask {id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete subtask: {str(e)}",
                operation="delete",
                table="task_subtasks"
            )
    
    def delete_by_parent_task_id(self, parent_task_id: TaskId) -> bool:
        """
        Delete all subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            True if any subtasks were deleted
        """
        try:
            with self.get_db_session() as session:
                result = session.query(TaskSubtask).filter(
                    TaskSubtask.task_id == parent_task_id.value
                ).delete()
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete subtasks for task: {str(e)}",
                operation="delete_by_parent_task_id",
                table="task_subtasks"
            )
    
    def exists(self, id: str) -> bool:
        """
        Check if a subtask exists by its ID.
        
        Args:
            id: Subtask ID string
            
        Returns:
            True if exists, False otherwise
        """
        try:
            with self.get_db_session() as session:
                return session.query(TaskSubtask).filter(
                    TaskSubtask.id == id
                ).first() is not None
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to check if subtask exists {id}: {e}")
            raise DatabaseException(
                message=f"Failed to check subtask existence: {str(e)}",
                operation="exists",
                table="task_subtasks"
            )
    
    def count_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """
        Count subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            Number of subtasks
        """
        try:
            with self.get_db_session() as session:
                return session.query(TaskSubtask).filter(
                    TaskSubtask.task_id == parent_task_id.value
                ).count()
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to count subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to count subtasks: {str(e)}",
                operation="count_by_parent_task_id",
                table="task_subtasks"
            )
    
    def count_completed_by_parent_task_id(self, parent_task_id: TaskId) -> int:
        """
        Count completed subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            Number of completed subtasks
        """
        try:
            with self.get_db_session() as session:
                return session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status == 'done'
                    )
                ).count()
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to count completed subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to count completed subtasks: {str(e)}",
                operation="count_completed_by_parent_task_id",
                table="task_subtasks"
            )
    
    def get_next_id(self, parent_task_id: TaskId) -> SubtaskId:
        """
        Get next available subtask ID for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            New SubtaskId
        """
        return SubtaskId.generate_new()
    
    def get_subtask_progress(self, parent_task_id: TaskId) -> Dict[str, Any]:
        """
        Get subtask progress statistics for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            Dictionary with progress statistics
        """
        try:
            with self.get_db_session() as session:
                # Get basic counts
                total_count = session.query(TaskSubtask).filter(
                    TaskSubtask.task_id == parent_task_id.value
                ).count()
                
                completed_count = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status == 'done'
                    )
                ).count()
                
                in_progress_count = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status == 'in_progress'
                    )
                ).count()
                
                blocked_count = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id.value,
                        TaskSubtask.status == 'blocked'
                    )
                ).count()
                
                # Calculate average progress percentage
                avg_progress = session.query(func.avg(TaskSubtask.progress_percentage)).filter(
                    TaskSubtask.task_id == parent_task_id.value
                ).scalar() or 0
                
                # Calculate completion percentage
                completion_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
                
                return {
                    "total_subtasks": total_count,
                    "completed_subtasks": completed_count,
                    "in_progress_subtasks": in_progress_count,
                    "blocked_subtasks": blocked_count,
                    "pending_subtasks": total_count - completed_count - in_progress_count - blocked_count,
                    "completion_percentage": round(completion_percentage, 1),
                    "average_progress": round(float(avg_progress), 1),
                    "has_blockers": blocked_count > 0
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to get subtask progress for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to get subtask progress: {str(e)}",
                operation="get_subtask_progress",
                table="task_subtasks"
            )
    
    def bulk_update_status(self, parent_task_id: TaskId, status: str) -> bool:
        """
        Update status of all subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            status: New status
            
        Returns:
            True if any subtasks were updated
        """
        try:
            with self.get_db_session() as session:
                update_data = {
                    TaskSubtask.status: status,
                    TaskSubtask.updated_at: datetime.now(timezone.utc)
                }
                
                # Add completion timestamp if marking as done
                if status == 'done':
                    update_data[TaskSubtask.completed_at] = datetime.now(timezone.utc)
                    update_data[TaskSubtask.progress_percentage] = 100
                elif status in ['todo', 'in_progress', 'blocked']:
                    update_data[TaskSubtask.completed_at] = None
                
                result = session.query(TaskSubtask).filter(
                    TaskSubtask.task_id == parent_task_id.value
                ).update(update_data)
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to bulk update status for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to bulk update status: {str(e)}",
                operation="bulk_update_status",
                table="task_subtasks"
            )
    
    def bulk_complete(self, parent_task_id: TaskId) -> bool:
        """
        Mark all subtasks as completed for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            True if any subtasks were updated
        """
        return self.bulk_update_status(parent_task_id, 'done')
    
    def remove_subtask(self, parent_task_id: str, subtask_id: str) -> bool:
        """
        Remove a subtask from a parent task by subtask ID.
        
        Args:
            parent_task_id: Parent task ID string
            subtask_id: Subtask ID string
            
        Returns:
            True if removed successfully
        """
        try:
            with self.get_db_session() as session:
                result = session.query(TaskSubtask).filter(
                    and_(
                        TaskSubtask.task_id == parent_task_id,
                        TaskSubtask.id == subtask_id
                    )
                ).delete()
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to remove subtask {subtask_id} from task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to remove subtask: {str(e)}",
                operation="remove_subtask",
                table="task_subtasks"
            )
    
    # Additional ORM-specific methods
    
    def update_progress(self, subtask_id: str, progress_percentage: int, 
                       progress_notes: str = "") -> bool:
        """
        Update subtask progress.
        
        Args:
            subtask_id: Subtask ID
            progress_percentage: Progress percentage (0-100)
            progress_notes: Optional progress notes
            
        Returns:
            True if updated successfully
        """
        try:
            with self.get_db_session() as session:
                result = session.query(TaskSubtask).filter(
                    TaskSubtask.id == subtask_id
                ).update({
                    TaskSubtask.progress_percentage: max(0, min(100, progress_percentage)),
                    TaskSubtask.progress_notes: progress_notes,
                    TaskSubtask.updated_at: datetime.now(timezone.utc)
                })
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to update progress for subtask {subtask_id}: {e}")
            raise DatabaseException(
                message=f"Failed to update progress: {str(e)}",
                operation="update_progress",
                table="task_subtasks"
            )
    
    def complete_subtask(self, subtask_id: str, completion_summary: str = "",
                        impact_on_parent: str = "", insights_found: List[str] = None) -> bool:
        """
        Complete a subtask with additional metadata.
        
        Args:
            subtask_id: Subtask ID
            completion_summary: Summary of completion
            impact_on_parent: Impact on parent task
            insights_found: List of insights found
            
        Returns:
            True if completed successfully
        """
        try:
            with self.get_db_session() as session:
                update_data = {
                    TaskSubtask.status: 'done',
                    TaskSubtask.progress_percentage: 100,
                    TaskSubtask.completed_at: datetime.now(timezone.utc),
                    TaskSubtask.updated_at: datetime.now(timezone.utc),
                    TaskSubtask.completion_summary: completion_summary,
                    TaskSubtask.impact_on_parent: impact_on_parent
                }
                
                if insights_found:
                    update_data[TaskSubtask.insights_found] = insights_found
                
                result = session.query(TaskSubtask).filter(
                    TaskSubtask.id == subtask_id
                ).update(update_data)
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to complete subtask {subtask_id}: {e}")
            raise DatabaseException(
                message=f"Failed to complete subtask: {str(e)}",
                operation="complete_subtask",
                table="task_subtasks"
            )
    
    def get_subtasks_by_assignee(self, assignee: str, limit: Optional[int] = None) -> List[Subtask]:
        """
        Get subtasks assigned to a specific assignee.
        
        Args:
            assignee: Assignee name/ID
            limit: Optional limit on number of results
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(TaskSubtask).filter(
                    TaskSubtask.assignees.contains([assignee])
                ).order_by(TaskSubtask.updated_at.desc())
                
                if limit:
                    query = query.limit(limit)
                
                models = query.all()
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to get subtasks by assignee {assignee}: {e}")
            raise DatabaseException(
                message=f"Failed to get subtasks by assignee: {str(e)}",
                operation="get_subtasks_by_assignee",
                table="task_subtasks"
            )
    
    # Private helper methods
    
    def _to_model_data(self, subtask: Subtask) -> Dict[str, Any]:
        """
        Convert domain entity to ORM model data.
        
        Args:
            subtask: Subtask domain entity
            
        Returns:
            Dictionary with model data
        """
        # Ensure assignees is a proper list of strings
        assignees = []
        if subtask.assignees:
            for assignee in subtask.assignees:
                if hasattr(assignee, 'value'):
                    # Handle AgentRole enum
                    assignees.append(f"@{assignee.value}")
                else:
                    # Handle string assignees
                    assignees.append(str(assignee))
        
        model_data = {
            "task_id": subtask.parent_task_id.value,
            "title": subtask.title,
            "description": subtask.description or "",
            "status": subtask.status.value if subtask.status else "todo",
            "priority": subtask.priority.value if subtask.priority else "medium",
            "assignees": assignees,
            "progress_percentage": getattr(subtask, 'progress_percentage', 0),  # Use actual progress_percentage
            "created_at": subtask.created_at or datetime.now(timezone.utc),
            "updated_at": subtask.updated_at or datetime.now(timezone.utc)
        }
        
        # Add user_id for data isolation
        model_data = self.set_user_id(model_data)
        return model_data
    
    def _to_domain_entity(self, model: TaskSubtask) -> Subtask:
        """
        Convert ORM model to domain entity.
        
        Args:
            model: TaskSubtask ORM model
            
        Returns:
            Subtask domain entity
        """
        # Convert assignees from JSON to list
        assignees = model.assignees if model.assignees else []
        
        # Create subtask using factory method
        subtask = Subtask(
            id=SubtaskId(model.id),
            title=model.title,
            description=model.description or "",
            parent_task_id=TaskId(model.task_id),
            status=TaskStatus.from_string(model.status),
            priority=Priority.from_string(model.priority),
            assignees=assignees,
            progress_percentage=model.progress_percentage or 0,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
        
        return subtask