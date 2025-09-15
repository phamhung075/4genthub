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
from ...domain.entities.global_context_schema import GlobalContextNestedData
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

    def _normalize_context_id(self, context_id: str) -> str:
        """
        Normalize context ID based on user context.

        For 'global_singleton':
        - If user_id is present, create a user-specific UUID
        - If no user_id, return the standard GLOBAL_SINGLETON_UUID

        For other IDs, return as-is.
        """
        from fastmcp.task_management.infrastructure.database.models import GLOBAL_SINGLETON_UUID
        import uuid

        # If not global_singleton, return as-is
        if context_id != "global_singleton":
            return context_id

        # Handle global_singleton based on user context
        if not self.user_id:
            # No user context, use the standard singleton UUID
            return GLOBAL_SINGLETON_UUID

        # Extract actual user ID from various formats
        actual_user_id = None
        if hasattr(self.user_id, 'user_id'):
            actual_user_id = self.user_id.user_id
        elif hasattr(self.user_id, 'id'):
            actual_user_id = self.user_id.id
        else:
            actual_user_id = str(self.user_id)

        # Create a deterministic UUID based on user ID
        try:
            # Use UUID5 with a namespace for deterministic generation
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard namespace UUID
            return str(uuid.uuid5(namespace, f"global_singleton:{actual_user_id}"))
        except Exception as e:
            logger.warning(f"Failed to create user-specific UUID: {e}, falling back to standard UUID")
            return GLOBAL_SINGLETON_UUID

    def create(self, entity: GlobalContext) -> GlobalContext:
        """Create a new global context for the current user with nested structure support."""
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
            
            # Ensure user_id is set - required for database constraint
            if not self.user_id:
                raise ValueError("user_id is required for global context creation. Repository must be scoped to a user.")
            
            # Use modern nested structure only
            nested_data = entity.get_nested_data()
            nested_structure_dict = nested_data.to_dict()
            
            # Extract structured data for database columns
            organization_standards = nested_structure_dict.get("organization", {}).get("standards", {})
            security_policies = nested_structure_dict.get("security", {}).get("access_control", {})
            compliance_requirements = nested_structure_dict.get("organization", {}).get("compliance", {})
            shared_resources = nested_structure_dict.get("operations", {}).get("resources", {})
            reusable_patterns = nested_structure_dict.get("development", {}).get("patterns", {})
            delegation_rules = nested_structure_dict.get("organization", {}).get("policies", {})
            combined_preferences = nested_structure_dict.get("preferences", {})
            
            # Create database model with both structures
            db_model = GlobalContextModel(
                id=entity.id,
                organization_id=entity.organization_name,
                # Flat structure (backward compatibility)
                organization_standards=organization_standards,
                security_policies=security_policies,
                compliance_requirements=compliance_requirements,
                shared_resources=shared_resources,
                reusable_patterns=reusable_patterns,
                global_preferences=combined_preferences,
                delegation_rules=delegation_rules,
                # Nested structure (v2.0)
                nested_structure=nested_structure_dict,
                # Unified context API compatibility - store complete data
                data=entity.global_settings or {},
                # Required fields
                user_id=self.user_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"Creating global context with nested structure for user {self.user_id}")
            
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
            
            logger.info(f"DEBUG: update - entity.global_settings = {global_settings}")
            
            # Map frontend fields to database columns
            # user_preferences maps to global_preferences
            user_preferences = global_settings.get("user_preferences", {})
            if user_preferences:
                global_preferences = user_preferences
            else:
                global_preferences = global_settings.get("global_preferences", {})
            
            organization_standards = global_settings.get("organization_standards", {})
            security_policies = global_settings.get("security_policies", {})
            compliance_requirements = global_settings.get("compliance_requirements", {})
            shared_resources = global_settings.get("shared_resources", {})
            reusable_patterns = global_settings.get("reusable_patterns", {})
            delegation_rules = global_settings.get("delegation_rules", {})
            
            # Handle custom fields (including frontend-specific fields)
            known_fields = {"organization_standards", "security_policies", "compliance_requirements",
                          "shared_resources", "reusable_patterns", "global_preferences", "delegation_rules",
                          "user_preferences"}  # user_preferences is already mapped above
            custom_fields = {}
            
            # Map frontend fields to custom fields for storage
            frontend_fields_mapping = {
                "ai_agent_settings": global_settings.get("ai_agent_settings", {}),
                "workflow_preferences": global_settings.get("workflow_preferences", {}),
                "development_tools": global_settings.get("development_tools", {}),
                "security_settings": global_settings.get("security_settings", {}),
                "dashboard_settings": global_settings.get("dashboard_settings", {})
            }
            
            # Add frontend fields to custom fields if they have values
            for field_name, field_value in frontend_fields_mapping.items():
                if field_value:
                    custom_fields[field_name] = field_value
            
            # Add any other unknown fields to custom fields
            for key, value in global_settings.items():
                if key not in known_fields and key not in frontend_fields_mapping:
                    custom_fields[key] = value
            
            if custom_fields:
                global_preferences["_custom"] = custom_fields
            
            # Use modern nested structure (similar to create method)
            nested_data = entity.get_nested_data()
            nested_structure_dict = nested_data.to_dict()
            
            # Extract structured data for database columns from nested structure
            organization_standards_nested = nested_structure_dict.get("organization", {}).get("standards", {})
            security_policies_nested = nested_structure_dict.get("security", {}).get("access_control", {})
            compliance_requirements_nested = nested_structure_dict.get("organization", {}).get("compliance", {})
            shared_resources_nested = nested_structure_dict.get("operations", {}).get("resources", {})
            reusable_patterns_nested = nested_structure_dict.get("development", {}).get("patterns", {})
            delegation_rules_nested = nested_structure_dict.get("organization", {}).get("policies", {})
            combined_preferences_nested = nested_structure_dict.get("preferences", {})
            
            # Merge flat structure fields with nested structure fields
            # Prefer non-empty values from either source
            db_model.organization_id = entity.organization_name
            db_model.organization_standards = organization_standards if organization_standards else organization_standards_nested
            db_model.security_policies = security_policies if security_policies else security_policies_nested
            db_model.compliance_requirements = compliance_requirements if compliance_requirements else compliance_requirements_nested
            db_model.shared_resources = shared_resources if shared_resources else shared_resources_nested
            db_model.reusable_patterns = reusable_patterns if reusable_patterns else reusable_patterns_nested
            db_model.global_preferences = global_preferences if global_preferences else combined_preferences_nested
            db_model.delegation_rules = delegation_rules if delegation_rules else delegation_rules_nested
            
            # CRITICAL: Update the nested structure field (this was missing!)
            db_model.nested_structure = nested_structure_dict

            # Update unified context API data field
            db_model.data = entity.global_settings or {}

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
        """Convert database model to domain entity with nested structure support."""
        
        # Check if nested structure exists in database
        nested_structure_dict = getattr(db_model, "nested_structure", None)
        schema_version = getattr(db_model, "schema_version", "1.0")
        is_migrated = getattr(db_model, "is_migrated", False)
        migration_warnings = getattr(db_model, "migration_warnings", None)
        
        # If we have a nested structure (schema version 2.0), use it as the primary source
        if nested_structure_dict and schema_version == "2.0":
            # Build global_settings from nested structure for frontend compatibility
            global_settings = {
                # Initialize default frontend fields
                "user_preferences": {},
                "ai_agent_settings": {"preferred_agents": []},
                "workflow_preferences": {},
                "development_tools": {},
                "security_settings": {},
                "dashboard_settings": {},
                "autonomous_rules": {},
                "security_policies": {},
                "coding_standards": {},
                "workflow_templates": {},
                "delegation_rules": {},
                "version": "1.0.0"
            }
            
            # Add the entire nested structure to global_settings
            # This preserves the organization, development, security, operations, preferences structure
            if nested_structure_dict:
                for key, value in nested_structure_dict.items():
                    if not key.startswith("_"):  # Skip internal fields
                        global_settings[key] = value
            
            # Extract specific fields from nested structure for frontend compatibility
            if "preferences" in nested_structure_dict:
                prefs = nested_structure_dict["preferences"]
                if "user_interface" in prefs:
                    global_settings["user_preferences"] = prefs.get("user_interface", {})
                if "agent_behavior" in prefs:
                    global_settings["ai_agent_settings"] = {"preferred_agents": [], **prefs.get("agent_behavior", {})}
                if "workflow" in prefs:
                    global_settings["workflow_preferences"] = prefs.get("workflow", {})
            
            if "development" in nested_structure_dict:
                dev = nested_structure_dict["development"]
                if "tools" in dev:
                    global_settings["development_tools"] = dev.get("tools", {})
                if "patterns" in dev:
                    global_settings["coding_standards"] = dev.get("patterns", {})
            
            if "security" in nested_structure_dict:
                sec = nested_structure_dict["security"]
                global_settings["security_settings"] = sec
                if "access_control" in sec:
                    global_settings["security_policies"] = sec.get("access_control", {})
            
            if "organization" in nested_structure_dict:
                org = nested_structure_dict["organization"]
                if "policies" in org and "agent_delegation" in org["policies"]:
                    global_settings["delegation_rules"] = org["policies"].get("agent_delegation", {})
            
            # Add schema version and custom categories
            if "_schema_version" in nested_structure_dict:
                global_settings["_schema_version"] = nested_structure_dict["_schema_version"]
            if "_custom_categories" in nested_structure_dict:
                global_settings["_custom_categories"] = nested_structure_dict["_custom_categories"]

        else:
            # Build global_settings from flat structure (backward compatibility)
            global_settings = {
                "organization_standards": getattr(db_model, "organization_standards", None) or {},
                "security_policies": db_model.security_policies or {},
                "compliance_requirements": getattr(db_model, "compliance_requirements", None) or {},
                "shared_resources": getattr(db_model, "shared_resources", None) or {},
                "reusable_patterns": getattr(db_model, "reusable_patterns", None) or {},
                "delegation_rules": db_model.delegation_rules or {}
            }
            
            # Handle preferences
            global_preferences = getattr(db_model, "global_preferences", None) or {}
            
            # Extract custom fields from global_preferences if they exist
            if "_custom" in global_preferences:
                global_preferences_copy = global_preferences.copy()
                custom_fields = global_preferences_copy.pop("_custom", {})
                
                # Extract frontend-specific fields from custom fields
                for field_name in ["ai_agent_settings", "workflow_preferences", "development_tools", 
                                  "security_settings", "dashboard_settings"]:
                    if field_name in custom_fields:
                        global_settings[field_name] = custom_fields[field_name]
                        
                # Add any remaining custom fields
                for key, value in custom_fields.items():
                    if key not in ["ai_agent_settings", "workflow_preferences", "development_tools",
                                   "security_settings", "dashboard_settings"]:
                        global_settings[key] = value
                        
                # Map global_preferences (without _custom) to user_preferences for frontend compatibility
                global_settings["user_preferences"] = global_preferences_copy
                global_settings["global_preferences"] = global_preferences_copy
            else:
                # Map global_preferences to user_preferences for frontend compatibility
                global_settings["user_preferences"] = global_preferences
                global_settings["global_preferences"] = global_preferences

        # Check for unified context API data field as primary source
        # This ensures data is preserved and prioritized for unified context operations
        data_field = getattr(db_model, "data", None)
        if data_field and isinstance(data_field, dict) and data_field:
            # Check if global_settings only contains empty or default values
            has_meaningful_data = False
            for key, value in global_settings.items():
                if value and key not in ["version", "_schema_version", "_custom_categories"]:
                    if isinstance(value, dict) and value != {}:
                        has_meaningful_data = True
                        break
                    elif isinstance(value, list) and value != []:
                        has_meaningful_data = True
                        break
                    elif value and not isinstance(value, (dict, list)):
                        has_meaningful_data = True
                        break

            if not has_meaningful_data:
                # Use data field as primary source when nested structure is empty
                logger.info(f"Using data field as primary source for global context {db_model.id}")
                global_settings = data_field.copy()
            else:
                # Merge data field into global_settings, prioritizing data field values
                logger.info(f"Merging data field with existing structure for global context {db_model.id}")
                for key, value in data_field.items():
                    # Always prefer data field values over empty nested structure values
                    if key not in global_settings or not global_settings[key] or global_settings[key] == {}:
                        global_settings[key] = value
                    elif isinstance(value, dict) and isinstance(global_settings.get(key), dict):
                        # Deep merge dictionaries, preferring data field content
                        global_settings[key].update(value)

        # Build metadata with nested structure information
        metadata = {
            "created_at": db_model.created_at.isoformat() if db_model.created_at else None,
            "updated_at": db_model.updated_at.isoformat() if db_model.updated_at else None,
            "version": db_model.version,
            "user_id": db_model.user_id,
            "schema_version": schema_version,
            "is_migrated": is_migrated
        }
        
        if migration_warnings:
            metadata["migration_warnings"] = migration_warnings
        
        if nested_structure_dict:
            metadata["nested_structure"] = nested_structure_dict
        
        # Create entity
        entity = GlobalContext(
            id=db_model.id,
            organization_name=db_model.organization_id or "",
            global_settings=global_settings,
            metadata=metadata
        )
        
        # Initialize nested structure from database if available
        if nested_structure_dict and schema_version == "2.0":
            try:
                entity._nested_data = GlobalContextNestedData.from_dict(nested_structure_dict)
                entity._is_migrated = is_migrated
                logger.debug(f"Loaded nested structure for global context {db_model.id}")
            except Exception as e:
                logger.warning(f"Failed to load nested structure for {db_model.id}: {e}")
                # Fall back to migration from flat structure
                entity._ensure_nested_structure()
        else:
            # Ensure nested structure is initialized
            entity._ensure_nested_structure()
        
        return entity
    
    def migrate_to_user_scoped(self) -> int:
        """
        Migrate existing global contexts to user-scoped contexts.
        Assigns existing contexts to the system user.
        
        Returns:
            Number of contexts migrated
        """
        import os
        system_user_id = os.getenv("SYSTEM_USER_ID")
        if not system_user_id:
            raise ValueError("SYSTEM_USER_ID environment variable is required for migration")
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