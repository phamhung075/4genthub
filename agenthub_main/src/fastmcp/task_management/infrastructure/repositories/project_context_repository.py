"""
Project Context Repository for unified context system.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from contextlib import contextmanager
import logging

from ...domain.entities.context import ProjectContext
from ...infrastructure.database.models import ProjectContext as ProjectContextModel
from .base_orm_repository import BaseORMRepository
from ..cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation

logger = logging.getLogger(__name__)


class ProjectContextRepository(CacheInvalidationMixin, BaseORMRepository):
    """Repository for project context operations."""
    
    def __init__(self, session_factory, user_id: Optional[str] = None):
        super().__init__(ProjectContextModel)
        self.session_factory = session_factory
        self.model_class = ProjectContextModel
        self.user_id = user_id
    
    def with_user(self, user_id: str) -> 'ProjectContextRepository':
        """Create a new repository instance scoped to a specific user."""
        return ProjectContextRepository(self.session_factory, user_id)
    
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
    
    def create(self, entity: ProjectContext) -> ProjectContext:
        """Create a new project context."""
        with self.get_db_session() as session:
            # Check if project context already exists
            existing = session.get(ProjectContextModel, entity.id)
            if existing:
                raise ValueError(f"Project context already exists: {entity.id}")
            
            # Use the entity's fields directly - no project_settings attribute exists
            # The entity already has properly structured fields from the service layer
            
            # Create new project context with proper field mapping (CONTEXT_DATA_MODELS.md)
            # CRITICAL: Set the id field (primary key) to entity.id
            db_model = ProjectContextModel(
                id=entity.id,  # This is the primary key
                project_id=entity.id,  # This is also needed for reference
                project_info=getattr(entity, 'project_info', {}) or {},
                team_preferences=entity.team_preferences or {},
                technology_stack=entity.technology_stack or {},
                project_workflow=entity.project_workflow or {},
                local_standards=entity.local_standards or {},
                project_settings=getattr(entity, 'project_settings', {}) or {},
                technical_specifications=getattr(entity, 'technical_specifications', {}) or {},
                global_overrides=entity.metadata.get('global_overrides', {}),
                delegation_rules=entity.metadata.get('delegation_rules', {}),
                user_id=self.user_id  # CRITICAL FIX: Never fallback to 'system' - require valid user_id
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
                level="project",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def get(self, context_id: str) -> Optional[ProjectContext]:
        """Get project context by ID."""
        with self.get_db_session() as session:
            query = session.query(ProjectContextModel).filter(ProjectContextModel.id == context_id)
            
            # Add user filter if user_id is set
            if self.user_id:
                query = query.filter(ProjectContextModel.user_id == self.user_id)
            
            db_model = query.first()
            return self._to_entity(db_model) if db_model else None
    
    def update(self, context_id: str, entity: ProjectContext) -> ProjectContext:
        """Update project context."""
        with self.get_db_session() as session:
            db_model = session.get(ProjectContextModel, context_id)
            if not db_model:
                raise ValueError(f"Project context not found: {context_id}")
            
            # Use the entity's fields directly - no project_settings attribute exists
            # The entity already has properly structured fields from the service layer
            
            # Update fields with proper mapping (CONTEXT_DATA_MODELS.md)
            db_model.project_info = getattr(entity, 'project_info', {}) or {}
            db_model.team_preferences = entity.team_preferences or {}
            db_model.technology_stack = entity.technology_stack or {}
            db_model.project_workflow = entity.project_workflow or {}
            db_model.local_standards = entity.local_standards or {}
            db_model.project_settings = getattr(entity, 'project_settings', {}) or {}
            db_model.technical_specifications = getattr(entity, 'technical_specifications', {}) or {}
            db_model.global_overrides = entity.metadata.get('global_overrides', {})
            db_model.delegation_rules = entity.metadata.get('delegation_rules', {})
            db_model.updated_at = datetime.now(timezone.utc)
            
            session.flush()
            # Don't refresh to avoid UUID conversion issues with SQLite
            # session.refresh(db_model)
            
            # Invalidate cache after update
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=context_id,
                operation=CacheOperation.UPDATE,
                user_id=self.user_id,
                level="project",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def delete(self, context_id: str) -> bool:
        """Delete project context."""
        with self.get_db_session() as session:
            db_model = session.get(ProjectContextModel, context_id)
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
                level="project",
                propagate=True
            )
            
            return True
    
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[ProjectContext]:
        """List project contexts."""
        with self.get_db_session() as session:
            stmt = select(ProjectContextModel)
            
            # Add user filter if user_id is set
            if self.user_id:
                stmt = stmt.where(ProjectContextModel.user_id == self.user_id)
            
            # Apply filters if provided
            if filters:
                if "project_id" in filters:
                    stmt = stmt.where(ProjectContextModel.project_id == filters["project_id"])
            
            result = session.execute(stmt)
            db_models = result.scalars().all()
            
            return [self._to_entity(model) for model in db_models]
    
    def _to_entity(self, db_model: ProjectContextModel) -> ProjectContext:
        """Convert database model to domain entity."""
        # Map database fields directly to entity fields (CONTEXT_DATA_MODELS.md)
        # Get project info or generate defaults
        project_info = getattr(db_model, 'project_info', {}) or {}
        project_name = project_info.get('name', f"Project-{db_model.project_id}")
        
        return ProjectContext(
            id=db_model.project_id,
            project_name=project_name,
            project_info=project_info,
            team_preferences=db_model.team_preferences or {},
            technology_stack=db_model.technology_stack or {},
            project_workflow=db_model.project_workflow or {},
            local_standards=db_model.local_standards or {},
            project_settings=getattr(db_model, 'project_settings', {}) or {},
            technical_specifications=getattr(db_model, 'technical_specifications', {}) or {},
            metadata={
                'global_overrides': db_model.global_overrides or {},
                'delegation_rules': db_model.delegation_rules or {},
                'created_at': db_model.created_at.isoformat() if db_model.created_at else None,
                'updated_at': db_model.updated_at.isoformat() if db_model.updated_at else None,
                'version': db_model.version
            }
        )