"""
Branch Context Repository for unified context system.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime, timezone
from contextlib import contextmanager
import logging
import uuid

from ...domain.entities.context import BranchContext
from ...infrastructure.database.models import BranchContext as BranchContextModel
from .base_orm_repository import BaseORMRepository
from ..cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation

logger = logging.getLogger(__name__)


def _normalize_uuid(uuid_value: any) -> str:
    """
    Normalize UUID to string format for consistent database operations.
    Handles UUID objects, strings, and None values.
    """
    if uuid_value is None:
        return str(uuid.uuid4())
    if hasattr(uuid_value, 'hex'):
        # UUID object
        return str(uuid_value)
    if isinstance(uuid_value, str):
        # Validate and return string UUID
        try:
            # This will raise ValueError if invalid UUID format
            uuid.UUID(uuid_value)
            return uuid_value
        except ValueError:
            logger.warning(f"Invalid UUID format: {uuid_value}, generating new UUID")
            return str(uuid.uuid4())
    # Fallback: generate new UUID
    return str(uuid.uuid4())


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
        """Override to use custom session factory with improved error handling."""
        if self._session:
            # Use existing session from transaction
            yield self._session
        else:
            # Use custom session factory
            session = self.session_factory()
            try:
                yield session
                session.commit()
            except IntegrityError as ie:
                session.rollback()
                logger.error(f"Database integrity error: {ie}")
                # Provide specific error context for constraint violations
                if "duplicate key" in str(ie).lower():
                    logger.error("Duplicate key constraint violation - record may already exist")
                elif "not null" in str(ie).lower():
                    logger.error("Not null constraint violation - required field is missing")
                elif "foreign key" in str(ie).lower():
                    logger.error("Foreign key constraint violation - referenced record doesn't exist")
                raise ie
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error: {e}")
                raise
            except Exception as e:
                session.rollback()
                logger.error(f"Unexpected error in database session: {e}")
                raise
            finally:
                session.close()
    
    def create(self, entity: BranchContext) -> BranchContext:
        """Create a new branch context with improved duplicate handling."""
        with self.get_db_session() as session:
            try:
                # Normalize the ID to ensure consistent format
                normalized_id = _normalize_uuid(entity.id)
                
                # Check if branch context already exists with user filtering
                query = session.query(BranchContextModel).filter(BranchContextModel.id == normalized_id)
                
                # Add user filter if user_id is set (consistent with get method)
                if self.user_id:
                    query = query.filter(BranchContextModel.user_id == self.user_id)
                
                existing = query.first()
                if existing:
                    logger.warning(f"Branch context already exists: {normalized_id}")
                    # Return existing entity instead of raising error for idempotency
                    return self._to_entity(existing)
                
                # Validate user_id is provided
                if not self.user_id:
                    raise ValueError("user_id is required for branch context creation")
                
                # Extract known fields from entity (matching CONTEXT_DATA_MODELS.md)
                branch_info = getattr(entity, 'branch_info', {}) or {}
                branch_workflow = getattr(entity, 'branch_workflow', {}) or {}
                feature_flags = getattr(entity, 'feature_flags', {}) or {}
                discovered_patterns = getattr(entity, 'discovered_patterns', {}) or {}
                branch_decisions = getattr(entity, 'branch_decisions', {}) or {}
                
                # Get legacy branch_settings for backwards compatibility
                branch_settings = entity.branch_settings or {}
                
                # Merge legacy settings into appropriate new fields
                if 'branch_workflow' in branch_settings:
                    branch_workflow.update(branch_settings['branch_workflow'])
                if 'branch_standards' in branch_settings:
                    branch_decisions.update(branch_settings.get('branch_standards', {}))
                if 'agent_assignments' in branch_settings:
                    branch_info['agent_assignments'] = branch_settings.get('agent_assignments', {})
                
                # Normalize project_id as well
                project_id = _normalize_uuid(entity.project_id) if entity.project_id else None
                
                # Combine all data into the data field (matching new model structure)
                data_field = {
                    'branch_info': branch_info,
                    'branch_workflow': branch_workflow,
                    'feature_flags': feature_flags,
                    'discovered_patterns': discovered_patterns,
                    'branch_decisions': branch_decisions,
                    'active_patterns': entity.metadata.get('active_patterns', {}),
                    'local_overrides': entity.metadata.get('local_overrides', {}),
                    'delegation_rules': entity.metadata.get('delegation_rules', {})
                }
                
                db_model = BranchContextModel(
                    id=normalized_id,  # Use normalized UUID as the primary key
                    branch_id=None,  # Set to NULL since this is a branch context ID, not a git branch reference
                    parent_project_id=project_id,  # This should reference project_contexts.id with proper format
                    data=data_field,
                    # Set new model fields directly
                    branch_info=branch_info,
                    branch_workflow=branch_workflow,
                    feature_flags=feature_flags,
                    discovered_patterns=discovered_patterns,
                    branch_decisions=branch_decisions,
                    active_patterns=entity.metadata.get('active_patterns', {}),
                    local_overrides=entity.metadata.get('local_overrides', {}),
                    delegation_rules=entity.metadata.get('delegation_rules', {}),
                    user_id=self.user_id  # FIXED: Always use provided user_id, no fallback
                )
                
                session.add(db_model)
                session.flush()
                
                # Invalidate cache after create
                self.invalidate_cache_for_entity(
                    entity_type="context",
                    entity_id=normalized_id,
                    operation=CacheOperation.CREATE,
                    user_id=self.user_id,
                    level="branch",
                    propagate=True
                )
                
                return self._to_entity(db_model)
                
            except IntegrityError as ie:
                session.rollback()
                logger.error(f"Integrity constraint violation creating branch context: {ie}")
                if "duplicate key" in str(ie).lower() or "unique constraint" in str(ie).lower():
                    # Handle duplicate key by returning existing record
                    existing = session.query(BranchContextModel).filter(
                        BranchContextModel.id == normalized_id
                    ).first()
                    if existing:
                        logger.info(f"Returning existing branch context after duplicate key error: {normalized_id}")
                        return self._to_entity(existing)
                raise ValueError(f"Branch context creation failed due to constraint violation: {str(ie)}")
            
            except Exception as e:
                session.rollback()
                logger.error(f"Unexpected error creating branch context: {e}")
                raise
    
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
            
            # Extract known fields from entity (matching CONTEXT_DATA_MODELS.md)
            branch_info = getattr(entity, 'branch_info', {}) or {}
            branch_workflow = getattr(entity, 'branch_workflow', {}) or {}
            feature_flags = getattr(entity, 'feature_flags', {}) or {}
            discovered_patterns = getattr(entity, 'discovered_patterns', {}) or {}
            branch_decisions = getattr(entity, 'branch_decisions', {}) or {}
            
            # Get legacy branch_settings for backwards compatibility
            branch_settings = entity.branch_settings or {}
            
            # Merge legacy settings into appropriate new fields
            if 'branch_workflow' in branch_settings:
                branch_workflow.update(branch_settings['branch_workflow'])
            if 'branch_standards' in branch_settings:
                branch_decisions.update(branch_settings.get('branch_standards', {}))
            if 'agent_assignments' in branch_settings:
                branch_info['agent_assignments'] = branch_settings.get('agent_assignments', {})
            
            # Update fields with proper mapping
            db_model.parent_project_id = entity.project_id
            db_model.branch_info = branch_info
            db_model.branch_workflow = branch_workflow
            db_model.feature_flags = feature_flags
            db_model.discovered_patterns = discovered_patterns
            db_model.branch_decisions = branch_decisions
            db_model.active_patterns = entity.metadata.get('active_patterns', {})
            
            # Update the data field with all information
            db_model.data = {
                'branch_info': branch_info,
                'branch_workflow': branch_workflow,
                'feature_flags': feature_flags,
                'discovered_patterns': discovered_patterns,
                'branch_decisions': branch_decisions,
                'active_patterns': entity.metadata.get('active_patterns', {}),
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
        
        # Get branch info from model or generate default
        branch_info = getattr(db_model, 'branch_info', {}) or data_field.get('branch_info', {})
        git_branch_name = branch_info.get('name', f"branch-{db_model.branch_id or db_model.id}")
        
        # Build legacy branch_settings for backwards compatibility
        branch_settings = {}
        if data_field:
            # Preserve any legacy fields in branch_settings
            if 'branch_standards' in data_field:
                branch_settings['branch_standards'] = data_field['branch_standards']
            if 'agent_assignments' in data_field:
                branch_settings['agent_assignments'] = data_field['agent_assignments']
        
        return BranchContext(
            id=db_model.id,  # Use the actual id field
            project_id=db_model.parent_project_id,
            git_branch_name=git_branch_name,
            branch_info=getattr(db_model, 'branch_info', {}) or data_field.get('branch_info', {}),
            branch_workflow=getattr(db_model, 'branch_workflow', {}) or data_field.get('branch_workflow', {}),
            feature_flags=getattr(db_model, 'feature_flags', {}) or data_field.get('feature_flags', {}),
            discovered_patterns=getattr(db_model, 'discovered_patterns', {}) or data_field.get('discovered_patterns', {}),
            branch_decisions=getattr(db_model, 'branch_decisions', {}) or data_field.get('branch_decisions', {}),
            branch_settings=branch_settings,  # Keep for backwards compatibility
            metadata={
                'active_patterns': getattr(db_model, 'active_patterns', {}) or data_field.get('active_patterns', {}),
                'local_overrides': db_model.local_overrides or data_field.get('local_overrides', {}),
                'delegation_rules': db_model.delegation_rules or data_field.get('delegation_rules', {}),
                'created_at': db_model.created_at.isoformat() if db_model.created_at else None,
                'updated_at': db_model.updated_at.isoformat() if db_model.updated_at else None
            }
        )