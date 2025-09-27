"""
ORM SubtaskEntity Repository Implementation using SQLAlchemy

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

from ...database.models import Subtask as SubtaskModel
from ...database.database_config import get_session
from ..base_orm_repository import BaseORMRepository
from ..base_timestamp_repository import BaseTimestampRepository
from ..base_user_scoped_repository import BaseUserScopedRepository
from ....domain.entities.subtask import Subtask as SubtaskEntity
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


class ORMSubtaskRepository(BaseTimestampRepository[SubtaskEntity], BaseUserScopedRepository, SubtaskRepository):
    """
    ORM implementation of SubtaskRepository using SQLAlchemy.
    
    Provides database operations for subtasks with proper data transformation
    between domain objects and ORM models.
    """
    
    def __init__(self, session=None, user_id: Optional[str] = None):
        """Initialize the ORM subtask repository with user isolation."""
        BaseORMRepository.__init__(self, SubtaskModel)
        # CRITICAL FIX: Pass None as session to BaseUserScopedRepository
        # This prevents creating an isolated session in __init__
        # The actual session will come from transaction() or get_db_session() context managers
        BaseUserScopedRepository.__init__(self, None, user_id)
    
    def save(self, subtask: SubtaskEntity) -> bool:
        """
        Save a subtask to the database.
        
        Args:
            subtask: SubtaskEntity domain entity
            
        Returns:
            True if saved successfully, False otherwise
        """
        logger.info(f"🔍 SUBTASK_SAVE: Starting save for user_id={self.user_id}, subtask_title='{subtask.title}'")
        try:
            # CRITICAL FIX: Use transaction context manager to ensure proper commit
            with self.transaction() as session:
                # Convert domain entity to ORM model data
                model_data = self._to_model_data(subtask)
                logger.info(f"🔍 SUBTASK_SAVE: Model data prepared with user_id={model_data.get('user_id')}")
                
                if subtask.id:
                    # Update existing subtask
                    existing = session.query(SubtaskModel).filter(
                        SubtaskModel.id == subtask.id.value
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in model_data.items():
                            if key != 'id':  # Don't update primary key
                                setattr(existing, key, value)
                        existing.touch("subtask_updated")
                        session.flush()
                        
                        # Update the domain entity with the persisted data
                        subtask.updated_at = existing.updated_at
                        logger.info(f"🔍 SUBTASK_SAVE: Updated existing subtask ID={subtask.id.value}")
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
                logger.info(f"🔍 SUBTASK_SAVE: Creating new subtask with data: {model_data}")
                new_subtask = SubtaskModel(**model_data)
                session.add(new_subtask)
                session.flush()
                logger.info(f"🔍 SUBTASK_SAVE: Flushed to database, ID={new_subtask.id}")
                session.refresh(new_subtask)
                
                # CRITICAL DEBUG: Verify persistence before commit
                verify = session.query(SubtaskModel).filter(SubtaskModel.id == new_subtask.id).first()
                logger.info(f"🔍 SUBTASK_SAVE: Verification query - found subtask: {verify is not None}")
                if verify:
                    logger.info(f"🔍 SUBTASK_SAVE: Verified subtask - ID={verify.id}, user_id={verify.user_id}, title='{verify.title}'")
                
                # Update domain entity with persisted timestamps
                subtask.created_at = new_subtask.created_at
                subtask.updated_at = new_subtask.updated_at
                
                logger.info(f"✅ SUBTASK_SAVE: Successfully completed save for subtask ID={new_subtask.id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to save subtask: {e}")
            raise DatabaseException(
                message=f"Failed to save subtask: {str(e)}",
                operation="save_subtask",
                table="subtasks"
            )
        except Exception as e:
            logger.error(f"Unexpected error saving subtask: {e}")
            return False
    
    def find_by_id(self, id: str) -> Optional[SubtaskEntity]:
        """
        Find a subtask by its ID with user filtering for multi-tenancy.

        Args:
            id: SubtaskEntity ID string

        Returns:
            SubtaskEntity domain entity or None if not found
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.id == id
                )

                # CRITICAL FIX: Apply user filter for multi-tenancy
                # This ensures users can only access their own subtasks
                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🔐 SUBTASK_SECURITY: Applied user filter for user_id={self.user_id}")
                else:
                    logger.warning(f"🚨 SUBTASK_SECURITY: No user_id available for filtering - this could cause data leakage")

                model = query.first()

                if model:
                    logger.info(f"✅ SUBTASK_FOUND: Found subtask id={id} for user_id={self.user_id}")
                    return self._to_domain_entity(model)
                else:
                    logger.info(f"❌ SUBTASK_NOT_FOUND: No subtask found with id={id} for user_id={self.user_id}")
                    return None

        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtask by id {id}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtask by id: {str(e)}",
                operation="find_by_id",
                table="subtasks"
            )
    
    def find_by_parent_task_id(self, parent_task_id: TaskId) -> List[SubtaskEntity]:
        """
        Find all subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.task_id == parent_task_id.value
                )
                
                # DEBUG: Log query before user filter
                logger.info(f"🐛 SUBTASK_DEBUG: Query before user filter: {query}")
                logger.info(f"🐛 SUBTASK_DEBUG: Looking for subtasks with task_id={parent_task_id.value}")
                logger.info(f"🐛 SUBTASK_DEBUG: Repository user_id={self.user_id}")
                
                # Apply standard user filter - user authentication required
                # CRITICAL FIX: Apply user filter directly to avoid model detection issues
                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🐛 SUBTASK_DEBUG: Applied user filter directly: user_id={self.user_id}")
                else:
                    logger.warning(f"🐛 SUBTASK_DEBUG: No user_id available for filtering - this could cause data leakage")
                
                # query = self.apply_user_filter(query)  # Replaced with direct filter above
                
                # DEBUG: Log query after user filter
                logger.info(f"🐛 SUBTASK_DEBUG: Query after user filter: {query}")
                
                models = query.order_by(SubtaskModel.created_at.asc()).all()
                
                # DEBUG: Log results
                logger.info(f"🐛 SUBTASK_DEBUG: Found {len(models)} subtask models")
                for model in models:
                    logger.info(f"🐛 SUBTASK_DEBUG: Model - id={model.id}, task_id={model.task_id}, user_id={model.user_id}, title={model.title}")
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks for task: {str(e)}",
                operation="find_by_parent_task_id",
                table="subtasks"
            )
    
    def find_by_assignee(self, assignee: str) -> List[SubtaskEntity]:
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
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.assignees.contains([assignee])
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(SubtaskModel.created_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks by assignee {assignee}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks by assignee: {str(e)}",
                operation="find_by_assignee",
                table="subtasks"
            )
    
    def find_by_status(self, status: str) -> List[SubtaskEntity]:
        """
        Find subtasks by status.
        
        Args:
            status: Status string
            
        Returns:
            List of subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.status == status
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(SubtaskModel.created_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find subtasks by status {status}: {e}")
            raise DatabaseException(
                message=f"Failed to find subtasks by status: {str(e)}",
                operation="find_by_status",
                table="subtasks"
            )
    
    def find_completed(self, parent_task_id: TaskId) -> List[SubtaskEntity]:
        """
        Find completed subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of completed subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status == 'done'
                    )
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(SubtaskModel.completed_at.desc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find completed subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find completed subtasks: {str(e)}",
                operation="find_completed",
                table="subtasks"
            )
    
    def find_pending(self, parent_task_id: TaskId) -> List[SubtaskEntity]:
        """
        Find pending subtasks for a parent task.
        
        Args:
            parent_task_id: Parent task ID
            
        Returns:
            List of pending subtask domain entities
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status.in_(['todo', 'in_progress', 'blocked'])
                    )
                )
                
                # Apply user filter for data isolation
                query = self.apply_user_filter(query)
                
                models = query.order_by(SubtaskModel.created_at.asc()).all()
                
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to find pending subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to find pending subtasks: {str(e)}",
                operation="find_pending",
                table="subtasks"
            )
    
    def delete(self, id: str) -> bool:
        """
        Delete a subtask by its ID with user filtering for multi-tenancy.

        Args:
            id: SubtaskEntity ID string

        Returns:
            True if deleted successfully, False if not found
        """
        try:
            # CRITICAL FIX: Use transaction context manager for write operations
            with self.transaction() as session:
                # CRITICAL SECURITY FIX: Apply user filter to prevent unauthorized deletion
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.id == id
                )

                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🔐 SUBTASK_SECURITY: Applied user filter in delete() for user_id={self.user_id}")
                else:
                    logger.warning(f"🚨 SUBTASK_SECURITY: No user_id available for filtering in delete() - this could allow unauthorized deletion")

                result = query.delete()
                logger.info(f"🗑️ SUBTASK_DELETE: Deleted {result} subtask(s) with id={id} for user_id={self.user_id}")

                return result > 0

        except SQLAlchemyError as e:
            logger.error(f"Failed to delete subtask {id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete subtask: {str(e)}",
                operation="delete",
                table="subtasks"
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
                result = session.query(SubtaskModel).filter(
                    SubtaskModel.task_id == parent_task_id.value
                ).delete()
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to delete subtasks for task: {str(e)}",
                operation="delete_by_parent_task_id",
                table="subtasks"
            )
    
    def exists(self, id: str) -> bool:
        """
        Check if a subtask exists by its ID with user filtering for multi-tenancy.

        Args:
            id: SubtaskEntity ID string

        Returns:
            True if exists, False otherwise
        """
        try:
            with self.get_db_session() as session:
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.id == id
                )

                # CRITICAL FIX: Apply user filter for multi-tenancy
                # This ensures users can only check existence of their own subtasks
                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🔐 SUBTASK_SECURITY: Applied user filter in exists() for user_id={self.user_id}")
                else:
                    logger.warning(f"🚨 SUBTASK_SECURITY: No user_id available for filtering in exists() - this could cause data leakage")

                result = query.first() is not None
                logger.info(f"🔍 SUBTASK_EXISTS: Subtask id={id} exists={result} for user_id={self.user_id}")
                return result

        except SQLAlchemyError as e:
            logger.error(f"Failed to check if subtask exists {id}: {e}")
            raise DatabaseException(
                message=f"Failed to check subtask existence: {str(e)}",
                operation="exists",
                table="subtasks"
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
                return session.query(SubtaskModel).filter(
                    SubtaskModel.task_id == parent_task_id.value
                ).count()
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to count subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to count subtasks: {str(e)}",
                operation="count_by_parent_task_id",
                table="subtasks"
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
                return session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status == 'done'
                    )
                ).count()
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to count completed subtasks for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to count completed subtasks: {str(e)}",
                operation="count_completed_by_parent_task_id",
                table="subtasks"
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
                total_count = session.query(SubtaskModel).filter(
                    SubtaskModel.task_id == parent_task_id.value
                ).count()
                
                completed_count = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status == 'done'
                    )
                ).count()
                
                in_progress_count = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status == 'in_progress'
                    )
                ).count()
                
                blocked_count = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id.value,
                        SubtaskModel.status == 'blocked'
                    )
                ).count()
                
                # Calculate average progress percentage
                avg_progress = session.query(func.avg(SubtaskModel.progress_percentage)).filter(
                    SubtaskModel.task_id == parent_task_id.value
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
                table="subtasks"
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
                    SubtaskModel.status: status
                    # BaseTimestampRepository handles updated_at automatically
                }
                
                # Add completion timestamp if marking as done
                if status == 'done':
                    # BaseTimestampRepository handles completed_at automatically
                    update_data[SubtaskModel.progress_percentage] = 100
                elif status in ['todo', 'in_progress', 'blocked']:
                    update_data[SubtaskModel.completed_at] = None
                
                result = session.query(SubtaskModel).filter(
                    SubtaskModel.task_id == parent_task_id.value
                ).update(update_data)
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to bulk update status for task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to bulk update status: {str(e)}",
                operation="bulk_update_status",
                table="subtasks"
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
            subtask_id: SubtaskEntity ID string
            
        Returns:
            True if removed successfully
        """
        try:
            with self.get_db_session() as session:
                result = session.query(SubtaskModel).filter(
                    and_(
                        SubtaskModel.task_id == parent_task_id,
                        SubtaskModel.id == subtask_id
                    )
                ).delete()
                
                return result > 0
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to remove subtask {subtask_id} from task {parent_task_id}: {e}")
            raise DatabaseException(
                message=f"Failed to remove subtask: {str(e)}",
                operation="remove_subtask",
                table="subtasks"
            )
    
    # Additional ORM-specific methods
    
    def update_progress(self, subtask_id: str, progress_percentage: int,
                       progress_notes: str = "") -> bool:
        """
        Update subtask progress with user filtering for multi-tenancy.

        Args:
            subtask_id: SubtaskEntity ID
            progress_percentage: Progress percentage (0-100)
            progress_notes: Optional progress notes

        Returns:
            True if updated successfully
        """
        try:
            # CRITICAL FIX: Use transaction context manager for write operations
            with self.transaction() as session:
                # CRITICAL SECURITY FIX: Apply user filter to prevent unauthorized updates
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.id == subtask_id
                )

                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🔐 SUBTASK_SECURITY: Applied user filter in update_progress() for user_id={self.user_id}")
                else:
                    logger.warning(f"🚨 SUBTASK_SECURITY: No user_id available for filtering in update_progress() - this could allow unauthorized updates")

                result = query.update({
                    SubtaskModel.progress_percentage: max(0, min(100, progress_percentage)),
                    SubtaskModel.progress_notes: progress_notes
                    # BaseTimestampRepository handles updated_at automatically
                })

                logger.info(f"📊 SUBTASK_PROGRESS: Updated {result} subtask(s) progress to {progress_percentage}% for user_id={self.user_id}")
                return result > 0

        except SQLAlchemyError as e:
            logger.error(f"Failed to update progress for subtask {subtask_id}: {e}")
            raise DatabaseException(
                message=f"Failed to update progress: {str(e)}",
                operation="update_progress",
                table="subtasks"
            )
    
    def complete_subtask(self, subtask_id: str, completion_summary: str = "",
                        impact_on_parent: str = "", insights_found: List[str] = None) -> bool:
        """
        Complete a subtask with additional metadata and user filtering for multi-tenancy.

        Args:
            subtask_id: SubtaskEntity ID
            completion_summary: Summary of completion
            impact_on_parent: Impact on parent task
            insights_found: List of insights found

        Returns:
            True if completed successfully
        """
        try:
            # CRITICAL FIX: Use transaction context manager for write operations
            with self.transaction() as session:
                # CRITICAL SECURITY FIX: Apply user filter to prevent unauthorized completion
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.id == subtask_id
                )

                if self.user_id:
                    query = query.filter(SubtaskModel.user_id == self.user_id)
                    logger.info(f"🔐 SUBTASK_SECURITY: Applied user filter in complete_subtask() for user_id={self.user_id}")
                else:
                    logger.warning(f"🚨 SUBTASK_SECURITY: No user_id available for filtering in complete_subtask() - this could allow unauthorized completion")

                update_data = {
                    SubtaskModel.status: 'done',
                    SubtaskModel.progress_percentage: 100,
                    # BaseTimestampRepository handles completed_at and updated_at automatically
                    SubtaskModel.completion_summary: completion_summary,
                    SubtaskModel.impact_on_parent: impact_on_parent
                }

                if insights_found:
                    update_data[SubtaskModel.insights_found] = insights_found

                result = query.update(update_data)
                logger.info(f"✅ SUBTASK_COMPLETE: Completed {result} subtask(s) with id={subtask_id} for user_id={self.user_id}")

                return result > 0

        except SQLAlchemyError as e:
            logger.error(f"Failed to complete subtask {subtask_id}: {e}")
            raise DatabaseException(
                message=f"Failed to complete subtask: {str(e)}",
                operation="complete_subtask",
                table="subtasks"
            )
    
    def get_subtasks_by_assignee(self, assignee: str, limit: Optional[int] = None) -> List[SubtaskEntity]:
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
                query = session.query(SubtaskModel).filter(
                    SubtaskModel.assignees.contains([assignee])
                ).order_by(SubtaskModel.updated_at.desc())
                
                if limit:
                    query = query.limit(limit)
                
                models = query.all()
                return [self._to_domain_entity(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to get subtasks by assignee {assignee}: {e}")
            raise DatabaseException(
                message=f"Failed to get subtasks by assignee: {str(e)}",
                operation="get_subtasks_by_assignee",
                table="subtasks"
            )
    
    # Private helper methods
    
    def _to_model_data(self, subtask: SubtaskEntity) -> Dict[str, Any]:
        """
        Convert domain entity to ORM model data.
        
        Args:
            subtask: SubtaskEntity domain entity
            
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
            "created_at": subtask.created_at,  # BaseTimestampRepository ensures this is set
            "updated_at": subtask.updated_at   # BaseTimestampRepository ensures this is set
        }
        
        # CRITICAL FIX: Explicit user_id handling - no complex fallbacks
        if not self.user_id:
            logger.error(f"🚨 SUBTASK_PERSISTENCE: No user_id available in repository")
            raise ValueError("User authentication required. No user ID provided for subtask creation.")
        
        # Explicit user_id assignment - this is the critical fix
        model_data['user_id'] = self.user_id
        logger.info(f"🔐 SUBTASK_PERSISTENCE_FIX: Explicitly set user_id={self.user_id} for subtask creation")
        
        return model_data
    
    def _to_domain_entity(self, model: SubtaskModel) -> SubtaskEntity:
        """
        Convert ORM model to domain entity.

        Args:
            model: SubtaskModel ORM model

        Returns:
            SubtaskEntity domain entity
        """
        # Convert assignees from JSON to list
        assignees = model.assignees if model.assignees else []
        
        # Create subtask using factory method
        subtask = SubtaskEntity(
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