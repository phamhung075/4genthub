"""
ORM Label Repository Implementation

This module implements the Label repository using SQLAlchemy ORM,
providing CRUD operations for labels and their relationships with tasks.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from ....domain.entities.label import Label as LabelEntity
from ....domain.entities.task import Task as TaskEntity
from ....domain.exceptions.base_exceptions import (
    NotFoundError,
    RepositoryError,
    ValidationError,
)
from ...database.database_adapter import DatabaseAdapter
from ...database.models import Label, Task, TaskLabel
from ..base_timestamp_repository import BaseTimestampRepository


class ORMLabelRepository(BaseTimestampRepository[Label]):
    """ORM-based Label repository implementation"""
    
    def __init__(self, db_adapter: DatabaseAdapter):
        super().__init__(Label)
        self._db_adapter = db_adapter
    
    def create_label(self, name: str, color: str = "#0066cc", description: str = "") -> LabelEntity:
        """
        Create a new label.
        
        Args:
            name: Label name
            color: Label color (hex format)
            description: Optional description
            
        Returns:
            Created label entity
            
        Raises:
            ValidationError: If label name already exists
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                # Check if label already exists
                existing = session.query(Label).filter(Label.name == name).first()
                if existing:
                    raise ValidationError(f"Label with name '{name}' already exists")
                
                # Create new label with default user_id
                import uuid
                effective_user_id = getattr(self, 'user_id', None)
                if not effective_user_id:
                    raise ValueError("user_id is required for label creation")
                    
                label = Label(
                    id=str(uuid.uuid4()),
                    name=name,
                    color=color,
                    description=description,
                    user_id=effective_user_id,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC)
                )
                
                session.add(label)
                session.commit()
                session.refresh(label)
                
                return self._model_to_entity(label)
                
        except ValidationError:
            raise
        except IntegrityError as e:
            error_msg = str(e)
            # Enhanced error messages for common constraint violations
            if "created_at" in error_msg or "updated_at" in error_msg:
                raise RepositoryError(
                    message=(
                        f"Label creation failed due to timestamp constraint violation. "
                        f"Timestamps must be timezone-aware UTC datetime objects. "
                        f"Use datetime.now(UTC) instead of datetime.now(). "
                        f"Technical details: {error_msg}"
                    )
                )
            elif "user_id" in error_msg:
                raise RepositoryError(
                    message=(
                        f"Label creation failed: user_id is required and must reference a valid user. "
                        f"Ensure authentication context is properly set. "
                        f"Technical details: {error_msg}"
                    )
                )
            elif "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
                raise ValidationError(
                    f"Label with name '{name}' already exists. Use a different name or update the existing label."
                )
            else:
                raise RepositoryError(
                    message=(
                        f"Label creation failed due to database constraint violation. "
                        f"Ensure all required fields (name, created_at, updated_at, user_id) are provided correctly. "
                        f"Technical details: {error_msg}"
                    )
                )
        except ValueError:
            # Let ValueError from domain validation propagate without wrapping
            # This allows tests to catch validation errors directly
            raise
        except Exception as e:
            raise RepositoryError(
                message=(
                    f"Unexpected error during label creation. "
                    f"Label name: '{name}', Color: '{color}'. "
                    f"Error: {str(e)}"
                )
            )
    
    def get_label(self, label_id: int) -> LabelEntity | None:
        """
        Get a label by ID.
        
        Args:
            label_id: Label ID
            
        Returns:
            Label entity or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                label = session.query(Label).filter(Label.id == label_id).first()
                return self._model_to_entity(label) if label else None
                
        except Exception as e:
            raise RepositoryError(message=f"Failed to get label: {str(e)}")
    
    def get_label_by_name(self, name: str) -> LabelEntity | None:
        """
        Get a label by name.
        
        Args:
            name: Label name
            
        Returns:
            Label entity or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                label = session.query(Label).filter(Label.name == name).first()
                return self._model_to_entity(label) if label else None
                
        except Exception as e:
            raise RepositoryError(message=f"Failed to get label by name: {str(e)}")
    
    def update_label(self, label_id: int, name: str | None = None,
                    color: str | None = None, description: str | None = None) -> LabelEntity:
        """
        Update a label using DDD-compliant pattern.

        Args:
            label_id: Label ID
            name: New name (optional)
            color: New color (optional)
            description: New description (optional)

        Returns:
            Updated label entity

        Raises:
            NotFoundError: If label not found
            ValidationError: If new name already exists
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                label = session.query(Label).filter(Label.id == label_id).first()
                if not label:
                    raise NotFoundError(resource_type="Label", resource_id=str(label_id))

                # Check if new name already exists (if name is being updated)
                if name and name != label.name:
                    existing = session.query(Label).filter(Label.name == name).first()
                    if existing:
                        raise ValidationError(f"Label with name '{name}' already exists")

                # DDD-COMPLIANT: Convert ORM model to domain entity
                label_entity = self._model_to_entity(label)

                # Update entity fields (domain layer validates business rules)
                if name is not None:
                    label_entity.name = name
                if color is not None:
                    label_entity.color = color
                if description is not None:
                    label_entity.description = description

                # Trigger entity validation
                label_entity._validate_entity()

                # DDD-COMPLIANT: Convert entity back to model dict
                model_dict = self._entity_to_model_dict(label_entity)

                # Update ORM model with data from entity
                label.name = model_dict["name"]
                label.color = model_dict["color"]
                label.description = model_dict["description"]

                session.commit()
                session.refresh(label)

                return self._model_to_entity(label)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise RepositoryError(message=f"Failed to update label: {str(e)}")
    
    def delete_label(self, label_id: int) -> bool:
        """
        Delete a label.
        
        Args:
            label_id: Label ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                label = session.query(Label).filter(Label.id == label_id).first()
                if not label:
                    return False
                
                session.delete(label)
                session.commit()
                return True
                
        except Exception as e:
            raise RepositoryError(message=f"Failed to delete label: {str(e)}")
    
    def list_labels(self, limit: int | None = None, 
                   offset: int | None = None) -> list[LabelEntity]:
        """
        List all labels.
        
        Args:
            limit: Maximum number of labels to return
            offset: Number of labels to skip
            
        Returns:
            List of label entities
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                query = session.query(Label).order_by(Label.name)
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                labels = query.all()
                return [self._model_to_entity(label) for label in labels]
                
        except Exception as e:
            raise RepositoryError(message=f"Failed to list labels: {str(e)}")
    
    def assign_label_to_task(self, task_id: str, label_id: int) -> bool:
        """
        Assign a label to a task.
        
        Args:
            task_id: Task ID
            label_id: Label ID
            
        Returns:
            True if assigned, False if already assigned
            
        Raises:
            NotFoundError: If task or label not found
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                # Check if task exists
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    raise NotFoundError(resource_type="Task", resource_id=task_id)
                
                # Check if label exists
                label = session.query(Label).filter(Label.id == label_id).first()
                if not label:
                    raise NotFoundError(resource_type="Label", resource_id=str(label_id))
                
                # Check if already assigned
                existing = session.query(TaskLabel).filter(
                    TaskLabel.task_id == task_id,
                    TaskLabel.label_id == label_id
                ).first()
                
                if existing:
                    return False
                
                # Create assignment with user_id for data isolation
                effective_user_id = getattr(self, 'user_id', None)
                if not effective_user_id:
                    raise ValueError("user_id is required for task label assignment")

                task_label = TaskLabel(
                    task_id=task_id,
                    label_id=label_id,
                    user_id=effective_user_id,
                    applied_at=datetime.now(UTC)
                )
                
                session.add(task_label)
                session.commit()
                return True
                
        except NotFoundError:
            raise
        except IntegrityError as e:
            error_msg = str(e)
            if "user_id" in error_msg:
                raise RepositoryError(
                    message=(
                        f"Failed to assign label to task: user_id is required. "
                        f"Ensure authentication context is properly set. "
                        f"Technical details: {error_msg}"
                    )
                )
            elif "foreign key" in error_msg.lower():
                raise RepositoryError(
                    message=(
                        f"Failed to assign label to task: Invalid task_id or label_id reference. "
                        f"Ensure both task (ID: {task_id}) and label (ID: {label_id}) exist. "
                        f"Technical details: {error_msg}"
                    )
                )
            else:
                raise RepositoryError(
                    message=(
                        f"Failed to assign label to task due to database constraint. "
                        f"Task ID: {task_id}, Label ID: {label_id}. "
                        f"Technical details: {error_msg}"
                    )
                )
        except Exception as e:
            raise RepositoryError(
                message=(
                    f"Unexpected error assigning label to task. "
                    f"Task ID: {task_id}, Label ID: {label_id}. "
                    f"Error: {str(e)}"
                )
            )
    
    def remove_label_from_task(self, task_id: str, label_id: int) -> bool:
        """
        Remove a label from a task.
        
        Args:
            task_id: Task ID
            label_id: Label ID
            
        Returns:
            True if removed, False if not assigned
            
        Raises:
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                task_label = session.query(TaskLabel).filter(
                    TaskLabel.task_id == task_id,
                    TaskLabel.label_id == label_id
                ).first()
                
                if not task_label:
                    return False
                
                session.delete(task_label)
                session.commit()
                return True
                
        except Exception as e:
            raise RepositoryError(message=f"Failed to remove label from task: {str(e)}")
    
    def get_tasks_by_label(self, label_id: int) -> list[TaskEntity]:
        """
        Get all tasks that have a specific label.
        
        Args:
            label_id: Label ID
            
        Returns:
            List of task entities
            
        Raises:
            NotFoundError: If label not found
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                # Check if label exists
                label = session.query(Label).filter(Label.id == label_id).first()
                if not label:
                    raise NotFoundError(resource_type="Label", resource_id=str(label_id))
                
                # Get tasks with this label
                tasks = session.query(Task).join(TaskLabel).filter(
                    TaskLabel.label_id == label_id
                ).all()
                
                return [self._task_model_to_entity(task) for task in tasks]
                
        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(message=f"Failed to get tasks by label: {str(e)}")
    
    def get_labels_by_task(self, task_id: str) -> list[LabelEntity]:
        """
        Get all labels assigned to a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of label entities
            
        Raises:
            NotFoundError: If task not found
            RepositoryError: If database operation fails
        """
        try:
            with self._db_adapter.get_session() as session:
                # Check if task exists
                task = session.query(Task).filter(Task.id == task_id).first()
                if not task:
                    raise NotFoundError(resource_type="Task", resource_id=task_id)
                
                # Get labels for this task
                labels = session.query(Label).join(TaskLabel).filter(
                    TaskLabel.task_id == task_id
                ).all()
                
                return [self._model_to_entity(label) for label in labels]
                
        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(message=f"Failed to get labels by task: {str(e)}")
    
    def _model_to_entity(self, model: Label) -> LabelEntity:
        """Convert Label model to LabelEntity"""
        return LabelEntity(
            id=model.id,
            name=model.name,
            color=model.color,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def _entity_to_model_dict(self, entity: LabelEntity) -> dict[str, Any]:
        """
        Convert LabelEntity to model dictionary for database updates.

        This method follows DDD principles by converting domain entities
        to infrastructure layer data structures.

        Args:
            entity: LabelEntity to convert

        Returns:
            Dictionary with model fields for database operations
        """
        return {
            "id": entity.id,
            "name": entity.name,
            "color": entity.color,
            "description": entity.description,
            "user_id": getattr(self, 'user_id', None)
        }

    def _task_model_to_entity(self, model: Task) -> TaskEntity:
        """Convert Task model to TaskEntity"""
        return TaskEntity(
            id=model.id,
            title=model.title,
            description=model.description,
            git_branch_id=model.git_branch_id,
            status=model.status,
            priority=model.priority,
            estimated_effort=model.estimated_effort,
            due_date=model.due_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
            context_id=model.context_id
        )