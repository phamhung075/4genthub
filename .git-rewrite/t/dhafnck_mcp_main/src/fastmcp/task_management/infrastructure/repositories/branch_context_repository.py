"""
Branch Context Repository for unified context system.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from contextlib import contextmanager
import logging

from ...domain.entities.context import BranchContext
from ...infrastructure.database.models import BranchContext as BranchContextModel
from .base_orm_repository import BaseORMRepository
from ..cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation

logger = logging.getLogger(__name__)


class BranchContextRepository(CacheInvalidationMixin, BaseORMRepository):
    """Repository for branch context operations."""
    
    def __init__(self, session_factory, user_id: Optional[str] = None):
        super().__init__(BranchContextModel)
        self.session_factory = session_factory
        self.user_id = user_id
    
    def with_user(self, user_id: str) -> 'BranchContextRepository':
        """Create a new repository instance scoped to a specific user."""
        return BranchContextRepository(self.session_factory, user_id)
    
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
    
    def create(self, entity: BranchContext) -> BranchContext:
        """Create a new branch context."""
        with self.get_db_session() as session:
            # Check if branch context already exists with user filtering
            query = session.query(BranchContextModel).filter(BranchContextModel.id == entity.id)
            
            # Add user filter if user_id is set (consistent with get method)
            if self.user_id:
                query = query.filter(BranchContextModel.user_id == self.user_id)
            
            existing = query.first()
            if existing:
                raise ValueError(f"Branch context already exists: {entity.id}")
            
            # Extract known fields and preserve custom fields
            branch_settings = entity.branch_settings or {}
            
            # Get predefined fields
            branch_workflow = branch_settings.get('branch_workflow', {})
            branch_standards = branch_settings.get('branch_standards', {})
            agent_assignments = branch_settings.get('agent_assignments', {})
            
            # Collect any custom fields not in the predefined set
            known_fields = {'branch_workflow', 'branch_standards', 'agent_assignments'}
            custom_fields = {}
            for key, value in branch_settings.items():
                if key not in known_fields:
                    custom_fields[key] = value
            
            # Store custom fields in branch_standards to preserve them
            if custom_fields:
                branch_standards['_custom'] = custom_fields
            
            # The issue was that branch_id was incorrectly set to entity.id, causing a foreign key 
            # constraint violation since branch_id references project_git_branchs.id
            # Setting branch_id to None since it's nullable and we don't need to reference a git branch
            
            # Use the entity data as provided, SQLAlchemy will handle UUID format conversion
            branch_id = entity.id
            project_id = entity.project_id or "default-project"
            
            # Combine all data into the data field
            data_field = {
                'branch_workflow': branch_workflow,
                'branch_standards': branch_standards,
                'agent_assignments': agent_assignments,
                'local_overrides': entity.metadata.get('local_overrides', {}),
                'delegation_rules': entity.metadata.get('delegation_rules', {})
            }
            
            db_model = BranchContextModel(
                id=branch_id,  # Use formatted entity.id as the primary key
                branch_id=None,  # Set to NULL since this is a branch context ID, not a git branch reference
                parent_project_id=project_id,  # This should reference project_contexts.id with proper format
                data=data_field,
                branch_workflow=branch_workflow,
                feature_flags={},  # Using feature_flags instead of branch_standards
                active_patterns={},  # Using active_patterns instead of agent_assignments
                local_overrides=entity.metadata.get('local_overrides', {}),
                delegation_rules=entity.metadata.get('delegation_rules', {}),
                user_id=self.user_id or entity.metadata.get('user_id')  # CRITICAL FIX: Never fallback to 'system' - require valid user_id
            )
            
            session.add(db_model)
            session.flush()
            # Don't refresh to avoid UUID conversion issues with SQLite
            # session.refresh(db_model)
            
            # Invalidate cache after create
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=branch_id,
                operation=CacheOperation.CREATE,
                user_id=self.user_id,
                level="branch",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def get(self, context_id: str) -> Optional[BranchContext]:
        """Get branch context by ID."""
        with self.get_db_session() as session:
            query = session.query(BranchContextModel).filter(BranchContextModel.id == context_id)
            
            # Add user filter if user_id is set
            if self.user_id:
                query = query.filter(BranchContextModel.user_id == self.user_id)
            
            db_model = query.first()
            return self._to_entity(db_model) if db_model else None
    
    def update(self, context_id: str, entity: BranchContext) -> BranchContext:
        """Update branch context."""
        with self.get_db_session() as session:
            db_model = session.get(BranchContextModel, context_id)
            if not db_model:
                raise ValueError(f"Branch context not found: {context_id}")
            
            # Extract known fields and preserve custom fields
            branch_settings = entity.branch_settings or {}
            
            # Get predefined fields
            branch_workflow = branch_settings.get('branch_workflow', {})
            branch_standards = branch_settings.get('branch_standards', {})
            agent_assignments = branch_settings.get('agent_assignments', {})
            
            # Collect any custom fields not in the predefined set
            known_fields = {'branch_workflow', 'branch_standards', 'agent_assignments'}
            custom_fields = {}
            for key, value in branch_settings.items():
                if key not in known_fields:
                    custom_fields[key] = value
            
            # Store custom fields in branch_standards to preserve them
            if custom_fields:
                branch_standards['_custom'] = custom_fields
            
            # Update fields with proper mapping
            db_model.parent_project_id = entity.project_id
            db_model.branch_workflow = branch_workflow
            db_model.feature_flags = {}  # Using feature_flags instead of branch_standards
            db_model.active_patterns = {}  # Using active_patterns instead of agent_assignments
            
            # Update the data field with all information
            db_model.data = {
                'branch_workflow': branch_workflow,
                'branch_standards': branch_standards,
                'agent_assignments': agent_assignments,
                'local_overrides': entity.metadata.get('local_overrides', {}),
                'delegation_rules': entity.metadata.get('delegation_rules', {})
            }
            db_model.local_overrides = entity.metadata.get('local_overrides', {})
            db_model.delegation_rules = entity.metadata.get('delegation_rules', {})
            db_model.user_id = self.user_id or entity.metadata.get('user_id') or db_model.user_id  # CRITICAL FIX: Never fallback to 'system'
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
                level="branch",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def delete(self, context_id: str) -> bool:
        """Delete branch context."""
        with self.get_db_session() as session:
            db_model = session.get(BranchContextModel, context_id)
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
                level="branch",
                propagate=True
            )
            
            return True
    
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[BranchContext]:
        """List branch contexts."""
        with self.get_db_session() as session:
            stmt = select(BranchContextModel)
            
            # Add user filter if user_id is set
            if self.user_id:
                stmt = stmt.where(BranchContextModel.user_id == self.user_id)
            
            # Apply filters if provided
            if filters:
                if "project_id" in filters:
                    stmt = stmt.where(BranchContextModel.parent_project_id == filters["project_id"])
                if "git_branch_name" in filters:
                    # TODO: Implement join with ProjectGitBranch to filter by name
                    # For now, skip this filter as it requires a JOIN
                    pass
            
            result = session.execute(stmt)
            db_models = result.scalars().all()
            
            return [self._to_entity(model) for model in db_models]
    
    def _to_entity(self, db_model: BranchContextModel) -> BranchContext:
        """Convert database model to domain entity."""
        # Extract data from the data field if available
        data_field = db_model.data or {}
        
        # Reconstruct branch_settings from data field or individual fields
        branch_settings = {
            'branch_workflow': data_field.get('branch_workflow') or db_model.branch_workflow or {},
            'branch_standards': data_field.get('branch_standards') or {},
            'agent_assignments': data_field.get('agent_assignments') or {}
        }
        
        # Extract custom fields from branch_standards if they exist
        branch_standards = branch_settings.get('branch_standards', {})
        if '_custom' in branch_standards:
            # Make a copy to avoid mutating the original
            branch_standards_copy = branch_standards.copy()
            custom_fields = branch_standards_copy.pop('_custom', {})
            # Add custom fields back to branch_settings at root level
            branch_settings.update(custom_fields)
            # Update branch_standards with the cleaned version
            branch_settings['branch_standards'] = branch_standards_copy
        
        return BranchContext(
            id=db_model.id,  # Use the actual id field
            project_id=db_model.parent_project_id,
            git_branch_name=f"branch-{db_model.branch_id}",  # Generate name from ID
            branch_settings=branch_settings,
            metadata={
                'local_overrides': db_model.local_overrides or {},
                'delegation_rules': db_model.delegation_rules or {},
                'created_at': db_model.created_at.isoformat() if db_model.created_at else None,
                'updated_at': db_model.updated_at.isoformat() if db_model.updated_at else None
            }
        )