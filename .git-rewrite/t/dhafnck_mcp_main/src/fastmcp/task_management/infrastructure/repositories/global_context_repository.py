"""
Global Context Repository with User Isolation.

CRITICAL: Global contexts are NOT truly global - they are user-scoped.
Each user has their own "global" context space.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from contextlib import contextmanager
import logging

from ...domain.entities.context import GlobalContext
from ...infrastructure.database.models import GlobalContext as GlobalContextModel
from .base_user_scoped_repository import BaseUserScopedRepository
from ..cache.cache_invalidation_mixin import CacheInvalidationMixin, CacheOperation

logger = logging.getLogger(__name__)


class GlobalContextRepository(CacheInvalidationMixin, BaseUserScopedRepository):
    """
    Repository for global context operations with user isolation.
    
    IMPORTANT: Despite the name "global", these contexts are scoped per user.
    Each user has their own set of global contexts that don't affect other users.
    """
    
    def __init__(self, session_factory, user_id: Optional[str] = None):
        """
        Initialize with session factory and user context.
        
        Args:
            session_factory: Factory for creating database sessions
            user_id: ID of the user whose global contexts to access
        """
        # Get a session for the base class initialization
        session = session_factory()
        super().__init__(session, user_id)
        self.session_factory = session_factory
        self.model_class = GlobalContextModel
        
        if user_id:
            logger.info(f"GlobalContextRepository initialized for user: {user_id}")
        else:
            logger.debug("GlobalContextRepository initialized in system mode during startup - use with caution (expected behavior)")
    
    
    @contextmanager
    def get_db_session(self):
        """Override to use custom session factory for testing."""
        if hasattr(self, '_session') and self._session:
            yield self._session
        else:
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
    
    def create(self, entity: GlobalContext) -> GlobalContext:
        """Create a new global context for the current user."""
        with self.get_db_session() as session:
            # Check if user already has a global context
            if self.user_id:
                existing = session.query(GlobalContextModel).filter(
                    and_(
                        GlobalContextModel.id == entity.id,  # Use the entity's ID
                        GlobalContextModel.user_id == self.user_id
                    )
                ).first()
            else:
                # No user_id - this shouldn't happen in production
                logger.warning("Checking for global context without user_id")
                existing = None
            
            if existing:
                raise ValueError(f"Global context already exists for user. Use update instead.")
            
            # Extract global settings and preserve custom fields
            global_settings = entity.global_settings or {}
            
            # Get the predefined fields
            autonomous_rules = global_settings.get("autonomous_rules", {})
            security_policies = global_settings.get("security_policies", {})
            coding_standards = global_settings.get("coding_standards", {})
            workflow_templates = global_settings.get("workflow_templates", {})
            delegation_rules = global_settings.get("delegation_rules", {})
            
            # Collect any custom fields
            known_fields = {"autonomous_rules", "security_policies", "coding_standards", 
                          "workflow_templates", "delegation_rules"}
            custom_fields = {}
            for key, value in global_settings.items():
                if key not in known_fields:
                    custom_fields[key] = value
            
            # Store custom fields in workflow_templates
            if custom_fields:
                workflow_templates["_custom"] = custom_fields
            
            # Create new global context with user_id
            # Use the entity's ID which has already been normalized by the service
            db_model = GlobalContextModel(
                id=entity.id,  # Use the entity's ID, not re-normalizing
                organization_id=None,  # Set to None since we don't have organization UUIDs
                autonomous_rules=autonomous_rules,
                security_policies=security_policies,
                coding_standards=coding_standards,
                workflow_templates=workflow_templates,
                delegation_rules=delegation_rules,
                user_id=self.user_id,  # Set user_id for isolation
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Log access for audit
            self.log_access("create", "global_context", db_model.id)
            
            session.add(db_model)
            session.flush()
            session.refresh(db_model)
            
            # Invalidate cache after create
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=db_model.id,
                operation=CacheOperation.CREATE,
                user_id=self.user_id,
                level="global",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def get(self, context_id: str) -> Optional[GlobalContext]:
        """Get global context by ID, filtered by user."""
        
        with self.get_db_session() as session:
            # Build query with user filter
            query = session.query(GlobalContextModel).filter(
                GlobalContextModel.id == context_id
            )
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            db_model = query.first()
            
            if not db_model:
                logger.debug(f"Global context not found for user {self.user_id}: {context_id}")
            else:
                self.log_access("read", "global_context", context_id)
            
            return self._to_entity(db_model) if db_model else None
    
    def update(self, context_id: str, entity: GlobalContext) -> GlobalContext:
        """Update global context for the current user."""
        
        with self.get_db_session() as session:
            # Build query with user filter
            query = session.query(GlobalContextModel).filter(
                GlobalContextModel.id == context_id
            )
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            db_model = query.first()
            
            if not db_model:
                raise ValueError(f"Global context not found for user {self.user_id}: {context_id}")
            
            # Ensure user ownership before update
            self.ensure_user_ownership(db_model)
            
            # Extract and update global settings
            global_settings = entity.global_settings or {}
            
            autonomous_rules = global_settings.get("autonomous_rules", {})
            security_policies = global_settings.get("security_policies", {})
            coding_standards = global_settings.get("coding_standards", {})
            workflow_templates = global_settings.get("workflow_templates", {})
            delegation_rules = global_settings.get("delegation_rules", {})
            
            # Handle custom fields
            known_fields = {"autonomous_rules", "security_policies", "coding_standards", 
                          "workflow_templates", "delegation_rules"}
            custom_fields = {}
            for key, value in global_settings.items():
                if key not in known_fields:
                    custom_fields[key] = value
            
            if custom_fields:
                workflow_templates["_custom"] = custom_fields
            
            # Update fields
            db_model.organization_id = entity.organization_name
            db_model.autonomous_rules = autonomous_rules
            db_model.security_policies = security_policies
            db_model.coding_standards = coding_standards
            db_model.workflow_templates = workflow_templates
            db_model.delegation_rules = delegation_rules
            db_model.updated_at = datetime.now(timezone.utc)
            
            # Log access for audit
            self.log_access("update", "global_context", context_id)
            
            session.flush()
            session.refresh(db_model)
            
            # Invalidate cache after update
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=context_id,
                operation=CacheOperation.UPDATE,
                user_id=self.user_id,
                level="global",
                propagate=True
            )
            
            return self._to_entity(db_model)
    
    def delete(self, context_id: str) -> bool:
        """Delete global context for the current user."""
        
        with self.get_db_session() as session:
            # Build query with user filter
            query = session.query(GlobalContextModel).filter(
                GlobalContextModel.id == context_id
            )
            
            # Apply user filter
            query = self.apply_user_filter(query)
            
            db_model = query.first()
            
            if not db_model:
                return False
            
            # Ensure user ownership before delete
            self.ensure_user_ownership(db_model)
            
            # Log access for audit
            self.log_access("delete", "global_context", context_id)
            
            session.delete(db_model)
            
            # Invalidate cache after delete
            self.invalidate_cache_for_entity(
                entity_type="context",
                entity_id=context_id,
                operation=CacheOperation.DELETE,
                user_id=self.user_id,
                level="global",
                propagate=True
            )
            
            return True
    
    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[GlobalContext]:
        """List all global contexts for the current user."""
        with self.get_db_session() as session:
            # Start with base query
            query = session.query(GlobalContextModel)
            
            # Apply user filter - CRITICAL for isolation
            query = self.apply_user_filter(query)
            
            # Apply additional filters if provided
            if filters:
                for key, value in filters.items():
                    if hasattr(GlobalContextModel, key):
                        query = query.filter(getattr(GlobalContextModel, key) == value)
            
            db_models = query.all()
            
            # Log access for audit
            self.log_access("list", "global_context", f"count={len(db_models)}")
            
            return [self._to_entity(model) for model in db_models]
    
    
    def count_user_contexts(self) -> int:
        """
        Count the number of global contexts for the current user.
        Should typically be 0 or 1.
        
        Returns:
            Number of global contexts for the user
        """
        with self.get_db_session() as session:
            query = session.query(GlobalContextModel)
            query = self.apply_user_filter(query)
            return query.count()
    
    def _to_entity(self, db_model: GlobalContextModel) -> GlobalContext:
        """Convert database model to domain entity."""
        # Map database model fields to domain entity
        global_settings = {
            "autonomous_rules": db_model.autonomous_rules or {},
            "security_policies": db_model.security_policies or {},
            "coding_standards": db_model.coding_standards or {},
            "workflow_templates": db_model.workflow_templates or {},
            "delegation_rules": db_model.delegation_rules or {}
        }
        
        # Extract custom fields from workflow_templates if they exist
        workflow_templates = db_model.workflow_templates or {}
        if "_custom" in workflow_templates:
            workflow_templates_copy = workflow_templates.copy()
            custom_fields = workflow_templates_copy.pop("_custom", {})
            global_settings.update(custom_fields)
            global_settings["workflow_templates"] = workflow_templates_copy
        
        metadata = {
            "created_at": db_model.created_at.isoformat() if db_model.created_at else None,
            "updated_at": db_model.updated_at.isoformat() if db_model.updated_at else None,
            "version": db_model.version,
            "user_id": db_model.user_id  # Include user_id in metadata
        }
        
        return GlobalContext(
            id=db_model.id,
            organization_name=db_model.organization_id,
            global_settings=global_settings,
            metadata=metadata
        )
    
    def migrate_to_user_scoped(self) -> int:
        """
        Migrate existing global contexts to user-scoped contexts.
        Assigns existing contexts to the system user.
        
        Returns:
            Number of contexts migrated
        """
        system_user_id = "00000000-0000-0000-0000-000000000000"
        migrated = 0
        
        with self.get_db_session() as session:
            # Find contexts without user_id
            contexts_to_migrate = session.query(GlobalContextModel).filter(
                GlobalContextModel.user_id == None
            ).all()
            
            for context in contexts_to_migrate:
                context.user_id = system_user_id
                migrated += 1
                logger.info(f"Migrated global context {context.id} to system user")
            
            if migrated > 0:
                session.commit()
                logger.info(f"Migrated {migrated} global contexts to user-scoped")
        
        return migrated