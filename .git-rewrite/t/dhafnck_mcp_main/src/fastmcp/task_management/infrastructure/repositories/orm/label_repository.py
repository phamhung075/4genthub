"""
ORM Label Repository Implementation

This module implements the Label repository using SQLAlchemy ORM,
providing CRUD operations for labels and their relationships with tasks.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime

from ...database.models import Label, TaskLabel, Task
from ...database.database_adapter import DatabaseAdapter
from ....domain.entities.label import Label as LabelEntity
from ....domain.entities.task import Task as TaskEntity
from ....domain.exceptions.base_exceptions import (
    RepositoryError,
    NotFoundError,
    ValidationError
)


class ORMLabelRepository:
    """ORM-based Label repository implementation"""
    
    def __init__(self, db_adapter: DatabaseAdapter):
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
                label = Label(
                    id=str(uuid.uuid4()),
                    name=name,
                    color=color,
                    description=description,
                    user_id=getattr(self, 'user_id', None) or 'system'  # Default user_id for shared labels
                )
                
                session.add(label)
                session.commit()
                session.refresh(label)
                
                return self._model_to_entity(label)
                
        except ValidationError:
            raise
        except Exception as e:
            raise RepositoryError(message=f"Failed to create label: {str(e)}")
    
    def get_label(self, label_id: int) -> Optional[LabelEntity]:
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
    
    def get_label_by_name(self, name: str) -> Optional[LabelEntity]:
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
    
    def update_label(self, label_id: int, name: Optional[str] = None, 
                    color: Optional[str] = None, description: Optional[str] = None) -> LabelEntity:
        """
        Update a label.
        
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
                
                # Update fields
                if name is not None:
                    label.name = name
                if color is not None:
                    label.color = color
                if description is not None:
                    label.description = description
                
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
    
    def list_labels(self, limit: Optional[int] = None, 
                   offset: Optional[int] = None) -> List[LabelEntity]:
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
                task_label = TaskLabel(
                    task_id=task_id,
                    label_id=label_id,
                    user_id=getattr(self, 'user_id', None) or 'system'  # CRITICAL: Add user_id for database constraint
                )
                
                session.add(task_label)
                session.commit()
                return True
                
        except NotFoundError:
            raise
        except Exception as e:
            raise RepositoryError(message=f"Failed to assign label to task: {str(e)}")
    
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
    
    def get_tasks_by_label(self, label_id: int) -> List[TaskEntity]:
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
    
    def get_labels_by_task(self, task_id: str) -> List[LabelEntity]:
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
            created_at=model.created_at
        )
    
    def _task_model_to_entity(self, model: Task) -> TaskEntity:
        """Convert Task model to TaskEntity"""
        return TaskEntity(
            id=model.id,
            title=model.title,
            description=model.description,
            git_branch_id=model.git_branch_id,
            status=model.status,
            priority=model.priority,
            details=model.details,
            estimated_effort=model.estimated_effort,
            due_date=model.due_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
            context_id=model.context_id
        )