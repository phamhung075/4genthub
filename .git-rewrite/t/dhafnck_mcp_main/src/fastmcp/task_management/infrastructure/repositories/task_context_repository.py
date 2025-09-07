"""
Task Context Repository for unified context system.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from contextlib import contextmanager
import logging

from ...domain.entities.context import TaskContextUnified as TaskContext
from ...infrastructure.database.models import TaskContext as TaskContextModel
from .base_orm_repository import BaseORMRepository
from ..cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation

logger = logging.getLogger(__name__)


class TaskContextRepository(CacheInvalidationMixin, BaseORMRepository):
    """Repository for task context operations."""
    
    def __init__(self, session_factory, user_id: Optional[str] = None):
        super().__init__(TaskContextModel)
        self.session_factory = session_factory
        self.user_id = user_id
    
    def with_user(self, user_id: str) -> 'TaskContextRepository':
        """Create a new repository instance scoped to a specific user."""
        return TaskContextRepository(self.session_factory, user_id)
    
    @contextmanager
    def get_db_session(self):
        """Override to use custom session factory for testing."""
        if self._session:
            # Use existing session from transaction
            yield self._session
        else:
            # Use custom session factory
            session = self.session_factory()
            try:
                yield session
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                session.close()
    
    def create(self, entity: TaskContext) -> TaskContext:
        """Create a new task context."""
        with self.get_db_session() as session:
            # Check if task context already exists (using task_id as primary key)
            existing = session.get(TaskContextModel, entity.id)
            if existing:
                raise ValueError(f"Task context already exists: {entity.id}")
            
            # Task data already supports any JSON, no need to extract custom fields
            # since task_data is a flexible JSON field
            task_data = entity.task_data or {}
            
            # Store insights, progress, and next_steps within task_data
            task_data['progress'] = entity.progress
            task_data['insights'] = entity.insights
            task_data['next_steps'] = entity.next_steps
            
            # Create new task context with unified schema
            db_model = TaskContextModel(
                id=entity.id,  # Set the primary key
                task_id=entity.id,
                parent_branch_id=entity.branch_id,
                parent_branch_context_id=entity.branch_id,  # Assuming branch_id serves as both
                task_data=task_data,
                local_overrides=entity.metadata.get('local_overrides', {}),
                implementation_notes=entity.metadata.get('implementation_notes', {}),
                delegation_triggers=entity.metadata.get('delegation_triggers', {}),
                inheritance_disabled=entity.metadata.get('inheritance_disabled', False),
                force_local_only=entity.metadata.get('force_local_only', False),
                user_id=self.user_id or entity.metadata.get('user_id') or 'system',
                version=1
            )
            
            session.add(db_model)
            session.flush()
            # Don't refresh to avoid UUID conversion issues with SQLite
            # session.refresh(db_model)
            
            # Invalidate cache after create
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=entity.id,
                operation=CacheOperation.CREATE,
                user_id=self.user_id,
                level="task",
                propagate=False  # Tasks don't need propagation
            )
            
            return self._to_entity(db_model)
    
    def get(self, context_id: str) -> Optional[TaskContext]:
        """Get task context by ID."""
        with self.get_db_session() as session:
            query = session.query(TaskContextModel).filter(TaskContextModel.id == context_id)
            
            # Add user filter if user_id is set
            if self.user_id:
                query = query.filter(TaskContextModel.user_id == self.user_id)
            
            db_model = query.first()
            return self._to_entity(db_model) if db_model else None
    
    def update(self, context_id: str, entity: TaskContext) -> TaskContext:
        """Update task context."""
        with self.get_db_session() as session:
            db_model = session.get(TaskContextModel, context_id)
            if not db_model:
                raise ValueError(f"Task context not found: {context_id}")
            
            # Task data already supports any JSON
            task_data = entity.task_data or {}
            
            # Store insights, progress, and next_steps within task_data
            task_data['progress'] = entity.progress
            task_data['insights'] = entity.insights
            task_data['next_steps'] = entity.next_steps
            
            # Update fields with unified schema
            db_model.parent_branch_id = entity.branch_id
            db_model.task_data = task_data
            db_model.local_overrides = entity.metadata.get('local_overrides', {})
            db_model.implementation_notes = entity.metadata.get('implementation_notes', {})
            db_model.delegation_triggers = entity.metadata.get('delegation_triggers', {})
            db_model.inheritance_disabled = entity.metadata.get('inheritance_disabled', False)
            db_model.force_local_only = entity.metadata.get('force_local_only', False)
            db_model.user_id = self.user_id or entity.metadata.get('user_id') or db_model.user_id
            db_model.version += 1
            
            session.flush()
            # Don't refresh to avoid UUID conversion issues with SQLite
            # session.refresh(db_model)
            
            # Invalidate cache after update
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=context_id,
                operation=CacheOperation.UPDATE,
                user_id=self.user_id,
                level="task",
                propagate=False  # Tasks don't need propagation
            )
            
            return self._to_entity(db_model)
    
    def delete(self, context_id: str) -> bool:
        """Delete task context."""
        with self.get_db_session() as session:
            db_model = session.get(TaskContextModel, context_id)
            if not db_model:
                return False
            
            session.delete(db_model)
            session.flush()
            
            # Invalidate cache after delete
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=context_id,
                operation=CacheOperation.DELETE,
                user_id=self.user_id,
                level="task",
                propagate=False  # Tasks don't need propagation
            )
            
            return True
    
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[TaskContext]:
        """List task contexts."""
        with self.get_db_session() as session:
            stmt = select(TaskContextModel)
            
            # Add user filter if user_id is set
            if self.user_id:
                stmt = stmt.where(TaskContextModel.user_id == self.user_id)
            
            # Apply filters if provided
            if filters:
                if "branch_id" in filters:
                    stmt = stmt.where(TaskContextModel.parent_branch_id == filters["branch_id"])
                if "inheritance_disabled" in filters:
                    stmt = stmt.where(TaskContextModel.inheritance_disabled == filters["inheritance_disabled"])
            
            result = session.execute(stmt)
            db_models = result.scalars().all()
            
            return [self._to_entity(model) for model in db_models]
    
    def _to_entity(self, db_model: TaskContextModel) -> TaskContext:
        """Convert database model to domain entity."""
        task_data = db_model.task_data or {}
        
        # Extract insights, progress, and next_steps from task_data
        progress = task_data.get('progress', 0)
        insights = task_data.get('insights', [])
        next_steps = task_data.get('next_steps', [])
        
        # Remove these fields from task_data to avoid duplication
        clean_task_data = {k: v for k, v in task_data.items() 
                          if k not in ['progress', 'insights', 'next_steps']}
        
        return TaskContext(
            id=db_model.task_id,
            branch_id=db_model.parent_branch_id,
            task_data=clean_task_data,
            progress=progress,
            insights=insights,
            next_steps=next_steps,
            metadata={
                'local_overrides': db_model.local_overrides or {},
                'implementation_notes': db_model.implementation_notes or {},
                'delegation_triggers': db_model.delegation_triggers or {},
                'inheritance_disabled': db_model.inheritance_disabled,
                'force_local_only': db_model.force_local_only,
                'version': db_model.version,
                'created_at': db_model.created_at.isoformat() if db_model.created_at else None,
                'updated_at': db_model.updated_at.isoformat() if db_model.updated_at else None
            }
        )