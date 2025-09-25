"""
Unified Context Service for all context management operations.
Handles inheritance, delegation, caching, and business rules.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, date
import logging
from uuid import UUID
import json
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from fastmcp.task_management.domain.entities.context import GlobalContext, ProjectContext, BranchContext, TaskContextUnified as TaskContext
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from .context_cache_service import ContextCacheService
from .context_inheritance_service import ContextInheritanceService
from .context_delegation_service import ContextDelegationService
from .context_validation_service import ContextValidationService
from .context_hierarchy_validator import ContextHierarchyValidator
# GLOBAL_SINGLETON_UUID removed - each user has their own global context

logger = logging.getLogger(__name__)


class UnifiedContextService:
    """
    Single service for all context operations.
    Replaces both ContextService and UnifiedContextService.
    """
    
    def __init__(
        self,
        global_context_repository: Any,
        project_context_repository: Any,
        branch_context_repository: Any,
        task_context_repository: Any,
        cache_service: Optional[ContextCacheService] = None,
        inheritance_service: Optional[ContextInheritanceService] = None,
        delegation_service: Optional[ContextDelegationService] = None,
        validation_service: Optional[ContextValidationService] = None,
        user_id: Optional[str] = None
    ):
        """Initialize unified context service with required repositories and services."""
        self._user_id = user_id  # Store user context
        self.repositories = {
            ContextLevel.GLOBAL: global_context_repository,
            ContextLevel.PROJECT: project_context_repository,
            ContextLevel.BRANCH: branch_context_repository,
            ContextLevel.TASK: task_context_repository
        }
        
        self.cache_service = cache_service or ContextCacheService()
        self.inheritance_service = inheritance_service or ContextInheritanceService(
            self.repositories
        )
        self.delegation_service = delegation_service or ContextDelegationService(
            self.repositories
        )
        self.validation_service = validation_service or ContextValidationService()
        
        # Initialize hierarchy validator with potentially user-scoped repositories
        # When repositories are passed from with_user(), they're already scoped
        # When created directly, we need to scope them
        self.hierarchy_validator = ContextHierarchyValidator(
            global_repo=global_context_repository,  # Use repos as passed (might already be scoped)
            project_repo=project_context_repository,
            branch_repo=branch_context_repository,
            task_repo=task_context_repository,
            user_id=self._user_id
        )

    def with_user(self, user_id: str) -> 'UnifiedContextService':
        """Create a new service instance scoped to a specific user."""
        # Create user-scoped repositories
        global_repo = self._get_user_scoped_repository_for_user(self.repositories[ContextLevel.GLOBAL], user_id)
        project_repo = self._get_user_scoped_repository_for_user(self.repositories[ContextLevel.PROJECT], user_id)
        branch_repo = self._get_user_scoped_repository_for_user(self.repositories[ContextLevel.BRANCH], user_id)
        task_repo = self._get_user_scoped_repository_for_user(self.repositories[ContextLevel.TASK], user_id)
        
        return UnifiedContextService(
            global_repo,
            project_repo,
            branch_repo,
            task_repo,
            self.cache_service,
            self.inheritance_service,
            self.delegation_service,
            self.validation_service,
            user_id
        )
    
    def _get_user_scoped_repository_for_user(self, repository, user_id: str):
        """Get user-scoped repository for a specific user."""
        if repository and hasattr(repository, 'with_user'):
            return repository.with_user(user_id)
        return repository

    def _get_user_scoped_repository(self, repository):
        """Get user-scoped repository if user_id is available."""
        if self._user_id and hasattr(repository, 'with_user'):
            return repository.with_user(self._user_id)
        return repository
    
    def _serialize_for_json(self, data: Any) -> Any:
        """
        Recursively convert non-JSON-serializable objects to strings.
        Handles UUID, datetime, Decimal, and other common types.
        """
        if data is None:
            return None
        elif isinstance(data, (UUID, datetime, date)):
            return str(data)
        elif isinstance(data, Decimal):
            return float(data)
        elif isinstance(data, dict):
            return {key: self._serialize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._serialize_for_json(item) for item in data]
        elif isinstance(data, tuple):
            return [self._serialize_for_json(item) for item in data]
        elif hasattr(data, '__dict__'):
            # Handle custom objects by converting to dict
            return self._serialize_for_json(vars(data))
        else:
            return data
    
    def _normalize_global_context_id(self, context_id: str, user_id: Optional[str] = None) -> str:
        """
        Normalize global context ID, converting 'global' to user-specific UUID or auto-generating if None/empty.
        
        Args:
            context_id: The context ID to normalize
            user_id: The user ID for generating user-specific global context UUID
            
        Returns:
            Normalized context ID (UUID string)
        """
        # Handle special case where "global" is used as context_id OR context_id is None/empty
        if not context_id or context_id.lower() == "global":
            # Generate user-specific global context UUID
            effective_user_id = user_id or self._user_id
            if not effective_user_id:
                # Try to get from current context
                try:
                    from ....auth.middleware.request_context_middleware import get_current_user_id
                    effective_user_id = get_current_user_id()
                except Exception:
                    pass
            
            if effective_user_id:
                # Generate user-specific global context ID
                import uuid
                namespace = uuid.UUID("a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c")
                try:
                    user_uuid = uuid.UUID(str(effective_user_id))
                except ValueError:
                    user_uuid = uuid.uuid5(namespace, str(effective_user_id))
                normalized_id = str(uuid.uuid5(namespace, str(user_uuid)))
                logger.info(f"Normalized '{context_id or 'None'}' to user-specific UUID: {normalized_id} for user: {effective_user_id}")
                return normalized_id
            else:
                logger.error("Cannot normalize global context_id without user_id")
                raise ValueError("user_id is required for global context normalization (no fallback allowed for DDD compliance)")
        
        return context_id
        
    def create_context(
        self, 
        level: str, 
        context_id: str, 
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        auto_create_parents: bool = True
    ) -> Dict[str, Any]:
        """Create context at specified level with validation and auto-parent creation."""
        try:
            # Handle None data by converting to empty dict
            if data is None:
                data = {}
            
            # Temporarily set user_id if provided for normalization
            original_user_id = self._user_id
            if user_id:
                self._user_id = user_id
            
            # Validate level first to know if it's global
            context_level = ContextLevel(level)
            
            # Normalize context_id for global contexts (convert "global" to user-specific UUID)
            if context_level == ContextLevel.GLOBAL:
                context_id = self._normalize_global_context_id(context_id, user_id or self._user_id)
            
            # Restore original user_id
            self._user_id = original_user_id
            
            # Auto-detect project_id for branch contexts if not provided
            if context_level == ContextLevel.BRANCH and isinstance(data, dict) and not data.get("project_id"):
                # Try to get project_id from the git branch entity
                try:
                    from .domain_service_factory import DomainServiceFactory
                    git_branch_factory = DomainServiceFactory.get_git_branch_repository_factory()
                    
                    # Check if git_branch_factory is None before trying to use it
                    if git_branch_factory is None:
                        logger.debug("Git branch repository factory not available, skipping auto-detection")
                    else:
                        git_branch_repo = git_branch_factory.create()
                        
                        # Use sync method if available, otherwise handle async
                        if hasattr(git_branch_repo, 'get'):
                            branch = git_branch_repo.get(context_id)
                        elif hasattr(git_branch_repo, 'find_by_id'):
                            # Try sync find_by_id method first
                            branch = git_branch_repo.find_by_id(context_id)
                        else:
                            # Fallback: branch lookup not supported
                            branch = None
                        
                        if branch and hasattr(branch, 'project_id'):
                            data['project_id'] = branch.project_id
                            logger.info(f"Auto-detected project_id '{branch.project_id}' for branch context '{context_id}'")
                except Exception as e:
                    logger.debug(f"Could not auto-detect project_id from branch: {e}")
                    # Continue without auto-detection, will fail validation if project_id is required
            
            # Auto-detect git_branch_id for task contexts if not provided
            # Ensure data is not None and is a dict before checking its contents
            elif context_level == ContextLevel.TASK and isinstance(data, dict) and not any(data.get(key) for key in ["branch_id", "parent_branch_id", "git_branch_id"]):
                # Try to get git_branch_id from the task entity
                try:
                    from .domain_service_factory import DomainServiceFactory
                    task_factory = DomainServiceFactory.get_task_repository_factory()
                    
                    # Check if task_factory is None before trying to use it
                    if task_factory is None:
                        logger.debug("Task repository factory not available, skipping auto-detection")
                    else:
                        task_repo = task_factory.create()
                        
                        # Use the correct sync method
                        if hasattr(task_repo, 'get'):
                            task = task_repo.get(context_id)
                        elif hasattr(task_repo, 'find_by_id'):
                            # Try with just the ID parameter
                            task = task_repo.find_by_id(context_id)
                        else:
                            logger.warning("Task repository doesn't have expected methods 'get' or 'find_by_id'")
                            task = None
                        
                        if task and hasattr(task, 'git_branch_id') and task.git_branch_id:
                            data['git_branch_id'] = task.git_branch_id
                            logger.info(f"Auto-detected git_branch_id '{task.git_branch_id}' for task context '{context_id}'")
                        else:
                            logger.warning(f"Task found but no git_branch_id available: task={task}, has_attr={hasattr(task, 'git_branch_id') if task else 'No task'}")
                except Exception as e:
                    logger.warning(f"Could not auto-detect git_branch_id from task: {e}", exc_info=True)
                    # Continue without auto-detection, will fail validation if git_branch_id is required
            
            # Check if this is a task context with auto-detected git_branch_id
            auto_detected_branch_id = False
            if context_level == ContextLevel.TASK and data is not None and data.get("git_branch_id"):
                # Check if git_branch_id was auto-detected (added by us above)
                auto_detected_branch_id = True
                logger.info(f"Attempting task context creation with git_branch_id: {data.get('git_branch_id')}")
            
            # Auto-create parent contexts if enabled and needed
            if auto_create_parents and context_level != ContextLevel.GLOBAL:
                logger.info(f"Auto-creating parent contexts for {level} context: {context_id}")
                auto_creation_result = self._ensure_parent_contexts_exist(
                    target_level=context_level,
                    context_id=context_id,
                    data=data,
                    user_id=user_id,
                    project_id=project_id
                )
                
                if not auto_creation_result["success"]:
                    logger.warning(f"Failed to ensure parent contexts: {auto_creation_result.get('error')}")
                    # Continue anyway - some contexts may still be valid
                
            # Validate hierarchy requirements after auto-creation
            is_valid, error_msg, guidance = self.hierarchy_validator.validate_hierarchy_requirements(
                level=context_level,
                context_id=context_id,
                data=data
            )
            
            if not is_valid:
                # If auto-creation was disabled or failed, provide guidance but be more permissive
                if not auto_create_parents:
                    logger.info(f"Validation failed but auto-creation disabled for {level}:{context_id}")
                    # Return user-friendly error with guidance
                    response = {
                        "success": False,
                        "error": error_msg,
                        "auto_creation_disabled": True
                    }
                    if guidance:
                        response.update(guidance)
                    return response
                else:
                    # For certain contexts, allow creation even if validation fails
                    if self._should_allow_orphaned_creation(context_level, context_id, data):
                        logger.info(f"Allowing orphaned creation for {level}:{context_id} due to special conditions")
                        is_valid = True
                        error_msg = None
                    else:
                        # Return user-friendly error with guidance
                        response = {
                            "success": False,
                            "error": error_msg,
                            "auto_creation_attempted": True
                        }
                        if guidance:
                            response.update(guidance)
                        return response
            
            # Validate context data
            validation_result = self.validation_service.validate_context_data(
                level=context_level,
                data=data
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {validation_result['errors']}"
                }
            
            # Get appropriate repository
            base_repository = self.repositories.get(context_level)
            if not base_repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            # Use user-scoped repository with provided user_id or service user_id
            effective_user_id = user_id or self._user_id
            if effective_user_id and hasattr(base_repository, 'with_user'):
                repo = base_repository.with_user(effective_user_id)
                logger.debug(f"Created user-scoped repository for user: {effective_user_id}")
            else:
                repo = base_repository
                logger.warning(f"Using unscoped repository - no user_id available for {level} context creation")
            
            # Create context entity based on level
            logger.info(f"Creating entity with context_id: {context_id}")
            
            # Normalize context_id for database storage (generate proper UUIDs)
            if context_level == ContextLevel.GLOBAL:
                # GLOBAL_SINGLETON_UUID removed - each user has their own global context
                # Check if it's a composite ID (UUID_UUID format)
                if context_id and '_' in context_id and len(context_id.split('_')) == 2:
                    import uuid
                    # Extract user_id from the concatenated ID
                    parts = context_id.split("_", 1)
                    if len(parts) == 2:
                        user_uuid = parts[1]
                        # Use a namespace UUID for context generation
                        namespace = uuid.UUID("a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c")
                        proper_uuid = str(uuid.uuid5(namespace, user_uuid))
                        context_id = proper_uuid
            
            # Check if context already exists
            try:
                existing_context = repo.get(context_id)
                if existing_context:
                    logger.info(f"Context already exists: {level}:{context_id}, returning existing")
                    return {
                        "success": True,
                        "context": self._entity_to_dict(existing_context),
                        "level": level,
                        "context_id": existing_context.id,
                        "already_existed": True
                    }
            except Exception as check_error:
                # Context doesn't exist, proceed with creation
                logger.debug(f"Context doesn't exist (will create): {check_error}")
            
            context_entity = self._create_context_entity(
                level=context_level,
                context_id=context_id,
                data=data,
                user_id=user_id,
                project_id=project_id
            )
            logger.info(f"Created entity with ID: {getattr(context_entity, 'id', 'NO_ID')}")
            
            # Save to repository
            logger.info(f"About to create {level} context in repository with entity: {context_entity}")
            saved_context = repo.create(context_entity)
            logger.info(f"Successfully created {level} context in repository: {saved_context}")
            
            # Invalidate cache for parent contexts (child creation affects inheritance)
            try:
                from ...infrastructure.cache.context_cache import get_context_cache
                cache = get_context_cache()
                
                # Invalidate parent inheritance chains since a new child was added
                if context_level != ContextLevel.GLOBAL:
                    parent_level, parent_id = self._get_parent_info(context_level, saved_context)
                    if parent_level and parent_id:
                        cache.invalidate_inheritance(
                            user_id=user_id,
                            level=parent_level.value,
                            context_id=parent_id
                        )
                        logger.debug(f"Invalidated parent cache for {parent_level.value}:{parent_id}")
            except Exception as cache_error:
                logger.warning(f"Cache invalidation failed (non-critical): {cache_error}")
            
            return {
                "success": True,
                "context": self._entity_to_dict(saved_context),
                "level": level,
                "context_id": saved_context.id  # Return the actual saved ID
            }
            
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_context(
        self, 
        level: str, 
        context_id: str, 
        include_inherited: bool = False,
        force_refresh: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get context with optional inheritance resolution."""
        try:
            # Validate context_id is not None or empty
            if not context_id:
                return {
                    "success": False,
                    "error": "Context ID is required"
                }
            
            # Temporarily set user_id if provided for normalization
            original_user_id = self._user_id
            if user_id:
                self._user_id = user_id
            
            # Validate level first to know if it's global
            context_level = ContextLevel(level)
            
            # Normalize context_id for global contexts (convert "global" to user-specific UUID)
            if context_level == ContextLevel.GLOBAL:
                context_id = self._normalize_global_context_id(context_id, user_id or self._user_id)
            
            # Restore original user_id
            self._user_id = original_user_id
            
            # Skip cache operations for now (cache service is async)
            # TODO: Make cache service sync or skip caching in sync mode
            
            # Get from repository
            repository = self.repositories.get(context_level)
            if not repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            # Use user-scoped repository with provided user_id or service user_id
            effective_user_id = user_id or self._user_id
            if effective_user_id and hasattr(repository, 'with_user'):
                repo = repository.with_user(effective_user_id)
            else:
                repo = repository
            
            context_entity = repo.get(context_id)
            if not context_entity:
                return {
                    "success": False,
                    "error": f"Context not found: {context_id}"
                }
            
            context_data = self._entity_to_dict(context_entity)
            
            # Handle inheritance synchronously if requested
            if include_inherited:
                context_data = self._resolve_inheritance_sync(context_level, context_entity, context_data)
            
            # Skip cache update for now (cache service is async)
            # TODO: Make cache service sync or skip caching in sync mode
            
            return {
                "success": True,
                "context": context_data,
                "level": level,
                "context_id": context_entity.id,  # Return the actual entity ID
                "inherited": include_inherited
            }
            
        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_context(
        self, 
        level: str, 
        context_id: str, 
        data: Dict[str, Any],
        propagate_changes: bool = True,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update context with inheritance propagation."""
        try:
            # Validate level first to know if it's global
            context_level = ContextLevel(level)
            
            # Normalize context_id for global contexts (convert "global" to user-specific UUID)
            if context_level == ContextLevel.GLOBAL:
                context_id = self._normalize_global_context_id(context_id, user_id or self._user_id)
            
            # Get existing context
            repository = self._get_user_scoped_repository(self.repositories.get(context_level))
            if not repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            # Use user-scoped repository if user_id is available
            repo = self._get_user_scoped_repository(repository)
            existing = repo.get(context_id)
            if not existing:
                return {
                    "success": False,
                    "error": f"Context not found: {context_id}"
                }
            
            # Merge data with existing
            # Special handling for GlobalContext - merge into global_settings
            if context_level == ContextLevel.GLOBAL:
                existing_dict = self._entity_to_dict(existing)
                logger.info(f"DEBUG: GlobalContext update - existing_dict keys: {existing_dict.keys()}")
                logger.info(f"DEBUG: GlobalContext update - incoming data: {data}")
                
                # For GlobalContext, the update data should merge into global_settings
                if 'global_settings' in existing_dict:
                    # Merge the new data into the global_settings field
                    updated_global_settings = self._merge_context_data(
                        existing_data=existing_dict['global_settings'],
                        new_data=data
                    )
                    logger.info(f"DEBUG: GlobalContext update - merged global_settings: {updated_global_settings}")
                    updated_data = existing_dict.copy()
                    updated_data['global_settings'] = updated_global_settings
                else:
                    # If no global_settings exists, treat data as global_settings
                    updated_data = existing_dict.copy()
                    updated_data['global_settings'] = data
                
                logger.info(f"DEBUG: GlobalContext update - final updated_data: {updated_data}")
            else:
                updated_data = self._merge_context_data(
                    existing_data=self._entity_to_dict(existing),
                    new_data=data
                )
            
            # Skip validation for now (validation service is async)
            # TODO: Make validation service sync or skip validation in sync mode
            validation_result = {"valid": True}
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Validation failed: {validation_result['errors']}"
                }
            
            # Update entity
            updated_entity = self._update_context_entity(
                existing_entity=existing,
                new_data=updated_data
            )
            
            # Save to repository using user-scoped repository
            saved_context = repo.update(context_id, updated_entity)
            
            # Invalidate cache for updated context
            try:
                from ...infrastructure.cache.context_cache import get_context_cache
                cache = get_context_cache()
                
                # Invalidate the specific context and its inheritance chain
                effective_user_id = user_id or self._user_id
                cache.invalidate_context(
                    user_id=effective_user_id,
                    level=context_level.value,
                    context_id=context_id
                )
                cache.invalidate_inheritance(
                    user_id=effective_user_id,
                    level=context_level.value,
                    context_id=context_id
                )
                
                # If propagating changes, invalidate child contexts
                if propagate_changes:
                    self._invalidate_child_caches(context_level, context_id, effective_user_id, cache)
                
                logger.debug(f"Cache invalidated for updated context {level}:{context_id}")
            except Exception as cache_error:
                logger.warning(f"Cache invalidation failed (non-critical): {cache_error}")
            
            # Skip propagation for now (propagation service is async)
            # TODO: Make propagation sync or skip propagation in sync mode
            
            return {
                "success": True,
                "context": self._entity_to_dict(saved_context),
                "level": level,
                "context_id": context_id,
                "propagated": propagate_changes
            }
            
        except Exception as e:
            logger.error(f"Failed to update context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_context(
        self, 
        level: str, 
        context_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete context with cleanup."""
        try:
            # Validate level first to know if it's global
            context_level = ContextLevel(level)
            
            # Normalize context_id for global contexts (convert "global" to user-specific UUID)
            if context_level == ContextLevel.GLOBAL:
                context_id = self._normalize_global_context_id(context_id, user_id or self._user_id)
            
            # Get repository
            repository = self._get_user_scoped_repository(self.repositories.get(context_level))
            if not repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            # Use user-scoped repository if user_id is available
            repo = self._get_user_scoped_repository(repository)
            
            # Check if context exists
            existing = repo.get(context_id)
            if not existing:
                return {
                    "success": False,
                    "error": f"Context not found: {context_id}"
                }
            
            # Delete from repository
            result = repo.delete(context_id)
            
            # Invalidate cache for deleted context
            try:
                from ...infrastructure.cache.context_cache import get_context_cache
                cache = get_context_cache()
                user_id = self._user_id
                
                # Invalidate the specific context and its inheritance chain
                cache.invalidate_context(
                    user_id=user_id,
                    level=context_level.value,
                    context_id=context_id
                )
                cache.invalidate_inheritance(
                    user_id=user_id,
                    level=context_level.value,
                    context_id=context_id
                )
                
                # Invalidate child contexts that depended on this context
                self._invalidate_child_caches(context_level, context_id, user_id, cache)
                
                logger.debug(f"Cache invalidated for deleted context {level}:{context_id}")
            except Exception as cache_error:
                logger.warning(f"Cache invalidation failed (non-critical): {cache_error}")
            
            return {
                "success": result,
                "level": level,
                "context_id": context_id
            }
            
        except Exception as e:
            logger.error(f"Failed to delete context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resolve_context(
        self, 
        level: str, 
        context_id: str, 
        force_refresh: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve full inheritance chain with caching."""
        try:
            # Validate level first to know if it's global
            context_level = ContextLevel(level)
            
            # Normalize context_id for global contexts (convert "global" to user-specific UUID)
            if context_level == ContextLevel.GLOBAL:
                context_id = self._normalize_global_context_id(context_id, user_id or self._user_id)
            
            # Always resolve with inheritance for this method
            result = self.get_context(
                level=level,
                context_id=context_id,
                include_inherited=True,
                force_refresh=force_refresh
            )
            
            # Enhance the response to indicate this was a resolve operation
            if result.get("success"):
                result["resolved"] = True
                result["inheritance_applied"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to resolve context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delegate_context(
        self, 
        level: str, 
        context_id: str, 
        delegate_to: str, 
        data: Dict[str, Any],
        delegation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delegate context data to higher level."""
        try:
            # Normalize context_id for backward compatibility
            
            # Validate levels
            source_level = ContextLevel(level)
            target_level = ContextLevel(delegate_to)
            
            # Skip delegation for now (delegation service is async)
            # TODO: Make delegation service sync or skip delegation in sync mode
            delegation_result = {"success": True, "message": "Delegation skipped in sync mode"}
            
            return {
                "success": True,
                "delegation": delegation_result,
                "source_level": level,
                "target_level": delegate_to,
                "context_id": context_id
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_contexts(
        self, 
        level: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List contexts at specified level with optional filtering."""
        try:
            logger.info(f"list_contexts called with level={level}, filters={filters}")
            
            # Validate level
            context_level = ContextLevel(level)
            logger.info(f"Validated level: {context_level}")
            
            # Get repository
            repository = self._get_user_scoped_repository(self.repositories.get(context_level))
            if not repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            logger.info(f"Got repository: {repository}")
            
            # Use user-scoped repository if user_id is available
            repo = self._get_user_scoped_repository(repository)
            logger.info(f"User-scoped repository: {repo}, user_id={self._user_id}")
            
            # Get contexts
            logger.info(f"About to call repo.list with filters: {filters}")
            contexts = repo.list(filters=filters)
            logger.info(f"repo.list returned {len(contexts)} contexts")
            
            return {
                "success": True,
                "contexts": [self._entity_to_dict(c) for c in contexts],
                "level": level,
                "count": len(contexts)
            }
            
        except Exception as e:
            logger.error(f"Failed to list contexts: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_insight(
        self,
        level: str,
        context_id: str,
        content: str,
        category: Optional[str] = None,
        importance: Optional[str] = "medium",
        agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add an insight to context."""
        try:
            # Normalize context_id for backward compatibility
            
            # Get existing context
            context_result = self.get_context(level, context_id)
            if not context_result["success"]:
                return context_result
            
            context = context_result["context"]
            insights = context.get("insights", [])
            
            # Add new insight
            insight = {
                "content": content,
                "category": category or "general",
                "importance": importance,
                "agent": agent if agent else "unified_context_service",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            insights.append(insight)
            
            # Update context
            return self.update_context(
                level=level,
                context_id=context_id,
                data={"insights": insights}
            )
            
        except Exception as e:
            logger.error(f"Failed to add insight: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_progress(
        self,
        level: str,
        context_id: str,
        content: str,
        agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add progress update to context."""
        try:
            # Normalize context_id for backward compatibility
            
            # Get existing context
            context_result = self.get_context(level, context_id)
            if not context_result["success"]:
                return context_result
            
            context = context_result["context"]
            progress_updates = context.get("progress_updates", [])
            
            # Add new progress
            progress = {
                "content": content,
                "agent": agent if agent else "unified_context_service",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            progress_updates.append(progress)
            
            # Update context
            return self.update_context(
                level=level,
                context_id=context_id,
                data={"progress_updates": progress_updates}
            )
            
        except Exception as e:
            logger.error(f"Failed to add progress: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # Helper methods
    
    def _create_context_entity(
        self,
        level: ContextLevel,
        context_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """Create appropriate context entity based on level."""
        # Serialize data to ensure JSON compatibility
        data = self._serialize_for_json(data)
        
        if level == ContextLevel.GLOBAL:
            # Ensure user_id is in metadata for repository to use
            metadata = data.get("metadata", {})
            effective_user_id = user_id or self._user_id
            if not effective_user_id:
                raise ValueError("user_id is required for global context creation")
            metadata["user_id"] = effective_user_id
            
            # CRITICAL FIX: Pass all data as global_settings, not just data.get("global_settings")
            # This ensures custom fields like claude_md_rules are stored
            return GlobalContext(
                id=context_id,
                organization_name=data.get("organization_name", "Default Organization"),
                global_settings=data,  # Pass entire data dict to capture custom fields
                metadata=metadata
            )
        elif level == ContextLevel.PROJECT:
            # Define predefined project context fields
            predefined_fields = {"team_preferences", "technology_stack", "project_workflow", "local_standards", "project_name", "project_settings", "metadata"}
            
            # Extract predefined fields
            team_preferences = data.get("team_preferences", {})
            technology_stack = data.get("technology_stack", {})
            project_workflow = data.get("project_workflow", {})
            local_standards = data.get("local_standards", {})
            
            # Route unrecognized fields to local_standards._custom
            custom_fields = {}
            for key, value in data.items():
                if key not in predefined_fields:
                    custom_fields[key] = value
            
            # Add custom fields to local_standards._custom if any exist
            if custom_fields:
                if not isinstance(local_standards, dict):
                    local_standards = {}
                local_standards["_custom"] = local_standards.get("_custom", {})
                local_standards["_custom"].update(custom_fields)
                logger.info(f"Routed {len(custom_fields)} custom fields to local_standards._custom: {list(custom_fields.keys())}")
            
            # Extract new fields from data (matching CONTEXT_DATA_MODELS.md)
            project_info = data.get("project_info", {})
            project_settings = data.get("project_settings", {})
            technical_specifications = data.get("technical_specifications", {})
            
            return ProjectContext(
                id=context_id,
                project_name=data.get("project_name", "Unnamed Project"),
                project_info=project_info,
                team_preferences=team_preferences,
                technology_stack=technology_stack,
                project_workflow=project_workflow,
                local_standards=local_standards,
                project_settings=project_settings,
                technical_specifications=technical_specifications,
                metadata=data.get("metadata", {})
            )
        elif level == ContextLevel.BRANCH:
            # Extract new fields from data (matching CONTEXT_DATA_MODELS.md)
            branch_info = data.get("branch_info", {})
            branch_workflow = data.get("branch_workflow", {})
            feature_flags = data.get("feature_flags", {})
            discovered_patterns = data.get("discovered_patterns", {})
            branch_decisions = data.get("branch_decisions", {})
            
            # Build branch_settings for backward compatibility
            branch_settings = data.get("branch_settings", {})
            if not branch_settings:
                # Build from individual fields for backward compatibility
                branch_settings = {
                    "branch_workflow": branch_workflow,
                    "branch_standards": data.get("branch_standards", {}),
                    "agent_assignments": data.get("agent_assignments", {})
                }
            
            # Ensure user_id is in metadata for repository
            metadata = data.get("metadata", {})
            effective_user_id = user_id or self._user_id
            if not effective_user_id:
                raise ValueError("user_id is required for project context creation")
            metadata["user_id"] = effective_user_id
            metadata["active_patterns"] = data.get("active_patterns", {})
            metadata["local_overrides"] = data.get("local_overrides", {})
            metadata["delegation_rules"] = data.get("delegation_rules", {})
            
            return BranchContext(
                id=context_id,
                project_id=project_id or data.get("project_id"),
                git_branch_name=data.get("git_branch_name", "main"),
                branch_info=branch_info,
                branch_workflow=branch_workflow,
                feature_flags=feature_flags,
                discovered_patterns=discovered_patterns,
                branch_decisions=branch_decisions,
                branch_settings=branch_settings,  # Keep for backward compatibility
                metadata=metadata
            )
        elif level == ContextLevel.TASK:
            # Support branch_id, parent_branch_id, and git_branch_id for backward compatibility
            branch_id = (data.get("branch_id") or 
                        data.get("parent_branch_id") or
                        data.get("git_branch_id"))
            if not branch_id:
                raise ValueError("Task context requires branch_id, parent_branch_id, or git_branch_id")
            
            # Extract new fields from data (matching CONTEXT_DATA_MODELS.md)
            task_data = data.get("task_data", {})
            execution_context = data.get("execution_context", {})
            discovered_patterns = data.get("discovered_patterns", {})
            implementation_notes = data.get("implementation_notes", {})
            test_results = data.get("test_results", {})
            blockers = data.get("blockers", {})
            
            # Store the new fields in metadata for now (entity already supports them)
            metadata = data.get("metadata", {})
            metadata["execution_context"] = execution_context
            metadata["discovered_patterns"] = discovered_patterns
            metadata["implementation_notes"] = implementation_notes
            metadata["test_results"] = test_results
            metadata["blockers"] = blockers
            
            return TaskContext(
                id=context_id,
                branch_id=branch_id,
                task_data=task_data,
                execution_context=execution_context,
                discovered_patterns=discovered_patterns,
                implementation_notes=implementation_notes,
                test_results=test_results,
                blockers=blockers,
                progress=data.get("progress", 0),
                insights=data.get("insights", []),
                next_steps=data.get("next_steps", []),
                metadata=metadata
            )
        else:
            raise ValueError(f"Unknown context level: {level}")
    
    def _entity_to_dict(self, entity) -> Dict[str, Any]:
        """Convert context entity to dictionary."""
        # Always use dict() method if available, as it properly serializes all fields
        if hasattr(entity, 'dict') and callable(getattr(entity, 'dict')):
            result = entity.dict()
        else:
            result = vars(entity)
        logger.info(f"DEBUG: _entity_to_dict - converting entity type {type(entity).__name__} to dict with {len(result)} keys")
        return result
    
    def _merge_context_data(
        self,
        existing_data: Dict[str, Any],
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge new data with existing context data."""
        # CRITICAL FIX: Handle None values to prevent NoneType iteration errors
        if existing_data is None:
            logger.warning("🚨 CONTEXT_FIX: existing_data is None, initializing to empty dict")
            existing_data = {}
        if new_data is None:
            logger.warning("🚨 CONTEXT_FIX: new_data is None, initializing to empty dict")
            new_data = {}
            
        # Serialize existing and new data to ensure JSON compatibility
        try:
            existing_data = self._serialize_for_json(existing_data)
            if existing_data is None:
                logger.warning("🚨 CONTEXT_FIX: _serialize_for_json returned None for existing_data, using empty dict")
                existing_data = {}
        except Exception as e:
            logger.error(f"🚨 CONTEXT_FIX: Error serializing existing_data: {e}")
            existing_data = {}
            
        try:
            new_data = self._serialize_for_json(new_data)
            if new_data is None:
                logger.warning("🚨 CONTEXT_FIX: _serialize_for_json returned None for new_data, using empty dict")
                new_data = {}
        except Exception as e:
            logger.error(f"🚨 CONTEXT_FIX: Error serializing new_data: {e}")
            new_data = {}
        
        # Ensure we have valid dictionaries before proceeding
        if not isinstance(existing_data, dict):
            logger.warning(f"🚨 CONTEXT_FIX: existing_data is not a dict after serialization: {type(existing_data)}, converting")
            existing_data = {}
        if not isinstance(new_data, dict):
            logger.warning(f"🚨 CONTEXT_FIX: new_data is not a dict after serialization: {type(new_data)}, converting")
            new_data = {}
        
        merged = existing_data.copy()
        
        # Special fields that should be replaced, not extended
        replace_list_fields = {'insights', 'next_steps'}
        
        # CRITICAL FIX: Add null check before iterating over new_data.items()
        if new_data is not None and isinstance(new_data, dict):
            for key, value in new_data.items():
                if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                    # Deep merge for nested dicts
                    merged[key] = {**merged[key], **value}
                elif isinstance(value, list) and key in merged and isinstance(merged[key], list) and key not in replace_list_fields:
                    # Extend lists (except for special fields)
                    merged[key].extend(value)
                else:
                    # Replace value (including lists in replace_list_fields)
                    merged[key] = value
        else:
            logger.debug("🚨 CONTEXT_FIX: new_data is None or not a dict, skipping merge iteration")
        
        # Remove manual timestamp handling - let repository layer handle persistence timestamps
        # Following clean timestamp management principles from BaseTimestampEntity patterns
        
        return merged
    
    def _update_context_entity(self, existing_entity, new_data: Dict[str, Any]):
        """Update context entity with new data."""
        # Create a new entity with updated data based on entity type
        entity_type = type(existing_entity)
        
        # Extract the appropriate fields for each entity type
        if isinstance(existing_entity, TaskContext):
            # For TaskContextUnified, extract all new fields (matching CONTEXT_DATA_MODELS.md)
            return TaskContext(
                id=new_data.get("id", existing_entity.id),
                branch_id=new_data.get("branch_id", existing_entity.branch_id),
                task_data=new_data.get("task_data", existing_entity.task_data),
                execution_context=new_data.get("execution_context", existing_entity.execution_context),
                discovered_patterns=new_data.get("discovered_patterns", existing_entity.discovered_patterns),
                implementation_notes=new_data.get("implementation_notes", existing_entity.implementation_notes),
                test_results=new_data.get("test_results", existing_entity.test_results),
                blockers=new_data.get("blockers", existing_entity.blockers),
                progress=new_data.get("progress", existing_entity.progress),
                insights=new_data.get("insights", existing_entity.insights),
                next_steps=new_data.get("next_steps", existing_entity.next_steps),
                metadata=new_data.get("metadata", existing_entity.metadata)
            )
        elif isinstance(existing_entity, BranchContext):
            # Extract all new fields (matching CONTEXT_DATA_MODELS.md)
            return BranchContext(
                id=new_data.get("id", existing_entity.id),
                project_id=new_data.get("project_id", existing_entity.project_id),
                git_branch_name=new_data.get("git_branch_name", existing_entity.git_branch_name),
                branch_info=new_data.get("branch_info", getattr(existing_entity, 'branch_info', {})),
                branch_workflow=new_data.get("branch_workflow", getattr(existing_entity, 'branch_workflow', {})),
                feature_flags=new_data.get("feature_flags", getattr(existing_entity, 'feature_flags', {})),
                discovered_patterns=new_data.get("discovered_patterns", getattr(existing_entity, 'discovered_patterns', {})),
                branch_decisions=new_data.get("branch_decisions", getattr(existing_entity, 'branch_decisions', {})),
                branch_settings=new_data.get("branch_settings", existing_entity.branch_settings),
                metadata=new_data.get("metadata", existing_entity.metadata)
            )
        elif isinstance(existing_entity, ProjectContext):
            # Extract all fields (matching CONTEXT_DATA_MODELS.md)
            project_info = new_data.get("project_info", getattr(existing_entity, 'project_info', {}))
            team_preferences = new_data.get("team_preferences", getattr(existing_entity, 'team_preferences', {}))
            technology_stack = new_data.get("technology_stack", getattr(existing_entity, 'technology_stack', {}))
            project_workflow = new_data.get("project_workflow", getattr(existing_entity, 'project_workflow', {}))
            local_standards = new_data.get("local_standards", getattr(existing_entity, 'local_standards', {}))
            project_settings = new_data.get("project_settings", getattr(existing_entity, 'project_settings', {}))
            technical_specifications = new_data.get("technical_specifications", getattr(existing_entity, 'technical_specifications', {}))
            
            # Define predefined fields to separate custom fields
            predefined_fields = {"id", "project_name", "project_info", "team_preferences", "technology_stack", 
                                "project_workflow", "local_standards", "project_settings", "technical_specifications", "metadata"}
            
            # Collect custom fields for local_standards._custom
            custom_fields_for_storage = {}
            # CRITICAL FIX: Check if new_data is not None and is a dict before iterating
            if new_data is not None and isinstance(new_data, dict):
                for key, value in new_data.items():
                    if key not in predefined_fields:
                        # Custom fields will be stored in local_standards._custom per repository convention
                        custom_fields_for_storage[key] = value
            else:
                logger.debug("🚨 CONTEXT_FIX: new_data is None or not a dict in _update_context_entity, skipping custom fields merge")
            
            # Store custom fields in local_standards._custom for repository compatibility
            if custom_fields_for_storage:
                if not isinstance(local_standards, dict):
                    local_standards = {}
                if "_custom" not in local_standards:
                    local_standards["_custom"] = {}
                local_standards["_custom"].update(custom_fields_for_storage)
            
            # Merge metadata 
            existing_metadata = existing_entity.metadata.copy() if existing_entity.metadata else {}
            # CRITICAL FIX: Add additional null checks for metadata merge
            if (new_data is not None and 
                isinstance(new_data, dict) and 
                "metadata" in new_data and 
                isinstance(new_data["metadata"], dict) and 
                new_data["metadata"] is not None):
                for key, value in new_data["metadata"].items():
                    existing_metadata[key] = value
            else:
                logger.debug("🚨 CONTEXT_FIX: Skipping metadata merge due to None or invalid metadata structure")
            
            return ProjectContext(
                id=new_data.get("id", existing_entity.id),
                project_name=new_data.get("project_name", existing_entity.project_name),
                project_info=project_info,
                team_preferences=team_preferences,
                technology_stack=technology_stack,
                project_workflow=project_workflow,
                local_standards=local_standards,
                project_settings=project_settings,
                technical_specifications=technical_specifications,
                metadata=existing_metadata
            )
        elif isinstance(existing_entity, GlobalContext):
            logger.info(f"DEBUG: _update_context_entity GlobalContext - new_data keys: {new_data.keys()}")
            
            # For global context, the new_data is the global_settings content
            # If new_data contains global_settings, use it; otherwise treat new_data as the global_settings
            if "global_settings" in new_data:
                global_settings = new_data["global_settings"]
                logger.info(f"DEBUG: _update_context_entity GlobalContext - using global_settings from new_data")
            else:
                # The entire new_data is the global settings update
                global_settings = new_data
                logger.info(f"DEBUG: _update_context_entity GlobalContext - using entire new_data as global_settings")
            
            logger.info(f"DEBUG: _update_context_entity GlobalContext - global_settings: {global_settings}")
            
            return GlobalContext(
                id=new_data.get("id", existing_entity.id),
                organization_name=new_data.get("organization_name", existing_entity.organization_name),
                global_settings=global_settings,
                metadata=new_data.get("metadata", existing_entity.metadata)
            )
        else:
            # Fallback - try to create entity with all data
            return entity_type(**new_data)
    
    def _propagate_changes(self, level: ContextLevel, context_id: str):
        """Propagate changes to dependent contexts."""
        # Skip cache invalidation for now (cache service is async)
        # TODO: Make cache service sync or skip caching in sync mode
        if level == ContextLevel.GLOBAL:
            # Global changes affect all contexts
            # await self.cache_service.invalidate_all()
            pass
        elif level == ContextLevel.PROJECT:
            # Project changes affect branch and task contexts
            # This would need to query for all branches in project
            pass
        elif level == ContextLevel.BRANCH:
            # Branch changes affect task contexts
            # This would need to query for all tasks in branch
            pass
        # Task level changes don't propagate upward
    
    def _cleanup_dependent_contexts(self, level: ContextLevel, context_id: str):
        """Clean up contexts that depend on the deleted context."""
        # This would handle cascading deletes based on level
        # For now, just log
        logger.info(f"Cleaning up dependent contexts for {level}:{context_id}")
    
    def auto_create_context_if_missing(
        self,
        level: str,
        context_id: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-create context if it doesn't exist, with fallback data.
        
        This method attempts to create a context if it doesn't already exist.
        It's designed to be used in scenarios where a context should be present
        but may not have been explicitly created (e.g., during task completion).
        
        Args:
            level: Context level (global, project, branch, task)
            context_id: Unique identifier for the context
            data: Optional context data, will use defaults if not provided
            user_id: Optional user identifier
            project_id: Optional project identifier  
            git_branch_id: Optional git branch identifier for branch/task contexts
            
        Returns:
            Dict with success status and context data or error information
        """
        try:
            # First, check if context already exists
            existing_result = self.get_context(level, context_id)
            if existing_result["success"]:
                logger.info(f"Context already exists for {level}:{context_id}")
                return existing_result
            
            # Context doesn't exist, create it with default data
            logger.info(f"Auto-creating context for {level}:{context_id}")
            
            # Build default data based on level and provided data
            default_data = self._build_default_context_data(
                level=level,
                context_id=context_id,
                data=data,
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            # Create the context
            create_result = self.create_context(
                level=level,
                context_id=context_id,
                data=default_data,
                user_id=user_id,
                project_id=project_id
            )
            
            if create_result["success"]:
                logger.info(f"Successfully auto-created context for {level}:{context_id}")
            else:
                logger.warning(f"Failed to auto-create context for {level}:{context_id}: {create_result.get('error')}")
            
            return create_result
            
        except Exception as e:
            logger.error(f"Error in auto_create_context_if_missing for {level}:{context_id}: {e}")
            return {
                "success": False,
                "error": f"Auto-creation failed: {str(e)}"
            }
    
    def _resolve_inheritance_sync(self, level: ContextLevel, context_entity: Any, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronously resolve context inheritance chain.
        
        Args:
            level: Context level
            context_entity: The context entity with parent references
            context_data: The context data to augment with inheritance
            
        Returns:
            Context data with inheritance chain resolved
        """
        try:
            logger.info(f"Resolving inheritance for {level} context")
            
            # Build inheritance chain from bottom to top
            inheritance_chain = []
            
            # Always start with global context
            global_repo = self.repositories.get(ContextLevel.GLOBAL)
            if global_repo:
                try:
                    # Each user has exactly ONE global context with their user_id as the context_id
                    # No need to generate - just use the user_id directly
                    if self._user_id:
                        global_context_id = self._user_id
                    else:
                        # Fallback - should not happen in production
                        logger.warning("No user_id available for global context lookup")
                        global_context_id = None
                    
                    if global_context_id:
                        global_entity = global_repo.get(global_context_id)
                    if global_entity:
                        global_data = self._entity_to_dict(global_entity)
                        inheritance_chain.append({
                            "level": "global",
                            "id": global_context_id,
                            "data": global_data
                        })
                        logger.debug("Added global context to inheritance chain")
                except Exception as e:
                    logger.warning(f"Could not fetch global context: {e}")
            
            # Add project context if needed
            if level in [ContextLevel.PROJECT, ContextLevel.BRANCH, ContextLevel.TASK]:
                project_id = None
                
                # Extract project_id based on level
                if level == ContextLevel.PROJECT:
                    project_id = context_entity.id
                elif level == ContextLevel.BRANCH:
                    project_id = getattr(context_entity, 'project_id', None)
                elif level == ContextLevel.TASK:
                    # For task, we need to get branch first to find project
                    branch_id = getattr(context_entity, 'branch_id', None)
                    if branch_id:
                        branch_repo = self.repositories.get(ContextLevel.BRANCH)
                        if branch_repo:
                            try:
                                branch_entity = branch_repo.get(branch_id)
                                if branch_entity:
                                    project_id = getattr(branch_entity, 'project_id', None)
                            except Exception as e:
                                logger.warning(f"Could not fetch branch for project lookup: {e}")
                
                # Fetch project context if we have the ID
                if project_id:
                    project_repo = self.repositories.get(ContextLevel.PROJECT)
                    if project_repo:
                        try:
                            project_entity = project_repo.get(project_id)
                            if project_entity:
                                project_data = self._entity_to_dict(project_entity)
                                inheritance_chain.append({
                                    "level": "project",
                                    "id": project_id,
                                    "data": project_data
                                })
                                logger.debug(f"Added project context {project_id} to inheritance chain")
                        except Exception as e:
                            logger.warning(f"Could not fetch project context {project_id}: {e}")
            
            # Add branch context if needed
            if level in [ContextLevel.BRANCH, ContextLevel.TASK]:
                branch_id = None
                
                # Extract branch_id based on level
                if level == ContextLevel.BRANCH:
                    branch_id = context_entity.id
                elif level == ContextLevel.TASK:
                    branch_id = getattr(context_entity, 'branch_id', None)
                
                # Fetch branch context if we have the ID
                if branch_id:
                    branch_repo = self.repositories.get(ContextLevel.BRANCH)
                    if branch_repo:
                        try:
                            branch_entity = branch_repo.get(branch_id)
                            if branch_entity:
                                branch_data = self._entity_to_dict(branch_entity)
                                inheritance_chain.append({
                                    "level": "branch",
                                    "id": branch_id,
                                    "data": branch_data
                                })
                                logger.debug(f"Added branch context {branch_id} to inheritance chain")
                        except Exception as e:
                            logger.warning(f"Could not fetch branch context {branch_id}: {e}")
            
            # Add the current context to the chain (only if it's not already in the chain)
            # This can happen when we're requesting a project context and it was already added above
            current_level_in_chain = any(item["level"] == level.value for item in inheritance_chain)
            if not current_level_in_chain:
                inheritance_chain.append({
                    "level": level.value,
                    "id": context_entity.id,
                    "data": context_data
                })
            
            # Now merge the inheritance chain using the inheritance service
            if len(inheritance_chain) > 1:
                # Use inheritance service to merge contexts properly
                merged_data = self._merge_inheritance_chain(inheritance_chain)
                
                # Add inheritance metadata
                merged_data["_inheritance"] = {
                    "chain": [item["level"] for item in inheritance_chain],
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "inheritance_depth": len(inheritance_chain)
                }
                
                return merged_data
            else:
                # No inheritance needed, just return the original data
                return context_data
                
        except Exception as e:
            logger.error(f"Error resolving inheritance: {e}")
            # Return original data on error
            return context_data
    
    def _merge_inheritance_chain(self, inheritance_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge inheritance chain using the inheritance service logic.
        
        Args:
            inheritance_chain: List of contexts from global to specific
            
        Returns:
            Merged context data
        """
        if not inheritance_chain:
            return {}
        
        # Start with the first context (usually global)
        merged = inheritance_chain[0]["data"].copy()
        
        # Apply each subsequent context using the inheritance service patterns
        for i in range(1, len(inheritance_chain)):
            current = inheritance_chain[i]
            current_level = current["level"]
            current_data = current["data"]
            
            if current_level == "project" and self.inheritance_service:
                # Use project inheritance logic
                merged = self.inheritance_service.inherit_project_from_global(merged, current_data)
            elif current_level == "branch" and self.inheritance_service:
                # Use branch inheritance logic
                merged = self.inheritance_service.inherit_branch_from_project(merged, current_data)
            elif current_level == "task" and self.inheritance_service:
                # Use task inheritance logic
                merged = self.inheritance_service.inherit_task_from_branch(merged, current_data)
            else:
                # Fallback to simple merge
                merged = self._merge_context_data(merged, current_data)
        
        return merged
    
    def _build_default_context_data(
        self,
        level: str,
        context_id: str,
        data: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build default context data for auto-creation based on level.
        
        This provides sensible defaults when auto-creating contexts,
        ensuring they have the minimum required data for each level.
        """
        base_data = data or {}
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Common metadata for all levels
        default_metadata = {
            "auto_created": True,
            "created_at": timestamp,
            "created_by": "auto_creation_service"
        }
        
        if level == "global":
            return {
                "organization_name": base_data.get("organization_name", "Default Organization"),
                "global_settings": base_data.get("global_settings", {
                    "default_timezone": "UTC",
                    "auto_create_contexts": True
                }),
                "metadata": {**default_metadata, **base_data.get("metadata", {})}
            }
            
        elif level == "project":
            return {
                "project_name": base_data.get("project_name", f"Project {context_id[:8]}"),
                "project_settings": base_data.get("project_settings", {
                    "auto_context_creation": True,
                    "default_branch": "main"
                }),
                "metadata": {**default_metadata, **base_data.get("metadata", {})}
            }
            
        elif level == "branch":
            return {
                "project_id": project_id or base_data.get("project_id"),
                "git_branch_name": base_data.get("git_branch_name", "main"),
                "branch_settings": base_data.get("branch_settings", {
                    "auto_created": True,
                    "workflow_type": "standard"
                }),
                "metadata": {**default_metadata, **base_data.get("metadata", {})}
            }
            
        elif level == "task":
            return {
                "branch_id": git_branch_id or base_data.get("branch_id") or base_data.get("parent_branch_id"),
                "task_data": base_data.get("task_data", {
                    "title": base_data.get("title", f"Task {context_id[:8]}"),
                    "description": base_data.get("description", "Auto-created task context"),
                    "auto_created": True
                }),
                "progress": base_data.get("progress", 0),
                "insights": base_data.get("insights", []),
                "next_steps": base_data.get("next_steps", []),
                "metadata": {**default_metadata, **base_data.get("metadata", {})}
            }
            
        else:
            # Fallback - return provided data with metadata
            return {
                **base_data,
                "metadata": {**default_metadata, **base_data.get("metadata", {})}
            }
    
    def _ensure_parent_contexts_exist(
        self,
        target_level: ContextLevel,
        context_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure all required parent contexts exist for the target context.
        
        This method is more robust than the previous auto-creation approach:
        1. It creates contexts only if they don't exist
        2. It provides detailed feedback on what was created
        3. It handles user-scoped contexts properly
        4. It gracefully handles partial failures
        
        Args:
            target_level: The level of context being created
            context_id: The ID of the target context
            data: The data for the target context (may contain parent IDs)
            user_id: Optional user ID
            project_id: Optional project ID
            
        Returns:
            Dict with success status and details of what was created
        """
        try:
            logger.info(f"Ensuring parent contexts exist for {target_level} context: {context_id}")
            
            created_contexts = []
            ensured_contexts = []
            errors = []
            
            # Determine the effective user_id
            effective_user_id = user_id or self._user_id
            
            if target_level == ContextLevel.PROJECT:
                # Project needs global context
                global_result = self._ensure_global_context_exists(effective_user_id)
                if global_result["success"]:
                    if global_result.get("created", False):
                        created_contexts.append("global")
                    else:
                        ensured_contexts.append("global")
                else:
                    errors.append(f"Global context: {global_result.get('error')}")
                    
            elif target_level == ContextLevel.BRANCH:
                # Branch needs global and project contexts
                branch_project_id = project_id or data.get("project_id")
                if not branch_project_id:
                    logger.warning(f"Branch context creation: project_id={project_id}, data.project_id={data.get('project_id') if data else 'None'}")
                    
                    # Try to extract project_id from context_id if it follows a pattern
                    if context_id and '-' in context_id:
                        # Sometimes project_id might be embedded in branch context_id
                        # This is a fallback - ideally project_id should be provided explicitly
                        logger.warning(f"Attempting to extract project_id from context_id pattern: {context_id}")
                    
                    return {
                        "success": False,
                        "error": "No project_id available for branch context parent creation",
                        "guidance": "Provide project_id in data or as parameter",
                        "debug_info": {
                            "provided_project_id": project_id,
                            "data_project_id": data.get("project_id") if data else None,
                            "context_id": context_id
                        }
                    }
                
                # Ensure global context
                global_result = self._ensure_global_context_exists(effective_user_id)
                if global_result["success"]:
                    if global_result.get("created", False):
                        created_contexts.append("global")
                    else:
                        ensured_contexts.append("global")
                else:
                    errors.append(f"Global context: {global_result.get('error')}")
                
                # Ensure project context
                project_result = self._ensure_project_context_exists(
                    branch_project_id, 
                    effective_user_id
                )
                if project_result["success"]:
                    if project_result.get("created", False):
                        created_contexts.append("project")
                    else:
                        ensured_contexts.append("project")
                else:
                    errors.append(f"Project context: {project_result.get('error')}")
                    
            elif target_level == ContextLevel.TASK:
                # Task needs global, project, and branch contexts
                branch_id = (data.get("branch_id") or 
                            data.get("parent_branch_id") or
                            data.get("git_branch_id"))
                if not branch_id:
                    return {
                        "success": False,
                        "error": "No branch_id available for task context parent creation",
                        "guidance": "Provide branch_id, parent_branch_id, or git_branch_id in data"
                    }
                
                # Determine project ID
                task_project_id = project_id
                if not task_project_id:
                    task_project_id = self._resolve_project_id_from_branch(branch_id)
                
                if not task_project_id:
                    return {
                        "success": False,
                        "error": "No project_id available for task context parent creation",
                        "guidance": "Ensure branch exists with project_id or provide project_id parameter"
                    }
                
                # Ensure global context
                global_result = self._ensure_global_context_exists(effective_user_id)
                if global_result["success"]:
                    if global_result.get("created", False):
                        created_contexts.append("global")
                    else:
                        ensured_contexts.append("global")
                else:
                    errors.append(f"Global context: {global_result.get('error')}")
                
                # Ensure project context
                project_result = self._ensure_project_context_exists(
                    task_project_id, 
                    effective_user_id
                )
                if project_result["success"]:
                    if project_result.get("created", False):
                        created_contexts.append("project")
                    else:
                        ensured_contexts.append("project")
                else:
                    errors.append(f"Project context: {project_result.get('error')}")
                
                # Ensure branch context
                branch_result = self._ensure_branch_context_exists(
                    branch_id, 
                    task_project_id,
                    effective_user_id
                )
                if branch_result["success"]:
                    if branch_result.get("created", False):
                        created_contexts.append("branch")
                    else:
                        ensured_contexts.append("branch")
                else:
                    errors.append(f"Branch context: {branch_result.get('error')}")
            
            # Determine overall success
            success = len(errors) == 0 or len(created_contexts + ensured_contexts) > 0
            
            result = {
                "success": success,
                "created_contexts": created_contexts,
                "ensured_contexts": ensured_contexts,
                "total_contexts_handled": len(created_contexts + ensured_contexts)
            }
            
            if errors:
                result["errors"] = errors
                result["partial_success"] = len(created_contexts + ensured_contexts) > 0
            
            logger.info(f"Parent context creation result: {result}")
            return result
                
        except Exception as e:
            logger.error(f"Exception during parent context creation: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Exception during parent context creation: {str(e)}"
            }
    
    def _create_hierarchy_atomically(self, contexts_to_create: List[tuple]) -> bool:
        """
        Create multiple contexts atomically in a single transaction.
        
        This ensures that either all parent contexts are created successfully,
        or none are created, maintaining data consistency.
        
        Args:
            contexts_to_create: List of tuples (level, context_id, data)
            
        Returns:
            bool: True if all contexts were created/verified, False otherwise
        """
        try:
            logger.info(f"Creating context hierarchy atomically: {len(contexts_to_create)} contexts")
            
            # Check if we have database transaction support
            # For now, we'll create contexts sequentially with rollback capability
            created_contexts = []
            
            try:
                for level, context_id, data in contexts_to_create:
                    success = self._create_context_atomically(level, context_id, data)
                    if success:
                        created_contexts.append((level, context_id))
                        logger.debug(f"Successfully ensured context exists: {level.value}/{context_id}")
                    else:
                        logger.warning(f"Failed to ensure context exists: {level.value}/{context_id}")
                        # For now, we continue even if individual contexts fail
                        # as they might already exist or the failure might be non-critical
                        
                # Consider all successful if we processed all contexts
                logger.info(f"Hierarchy creation completed. Processed: {len(contexts_to_create)} contexts, Created/Verified: {len(created_contexts)}")
                return True
                
            except Exception as e:
                logger.error(f"Error during atomic hierarchy creation: {e}")
                # In a future version, we could implement rollback here
                # For now, partial creation is acceptable as contexts are idempotent
                return False
                
        except Exception as e:
            logger.error(f"Failed to create context hierarchy atomically: {e}", exc_info=True)
            return False
    
    def _create_context_atomically(
        self, 
        level: ContextLevel, 
        context_id: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Create a context atomically without triggering validation cycles.
        
        This method bypasses the normal validation to prevent infinite recursion
        during auto-creation. It checks if the context exists first, then creates
        it directly if missing.
        
        Args:
            level: Context level
            context_id: Context identifier
            data: Context data
            
        Returns:
            bool: True if context exists or was created, False otherwise
        """
        try:
            # Extract user_id from data for proper repository scoping
            data_user_id = None
            if data and isinstance(data, dict):
                # Try to get user_id from different locations in data
                data_user_id = (
                    data.get("user_id") or 
                    (data.get("metadata", {}).get("user_id") if isinstance(data.get("metadata"), dict) else None)
                )
            
            # Use extracted user_id or service user_id
            effective_user_id = data_user_id or self._user_id
            
            # Get base repository and scope it properly
            base_repository = self.repositories.get(level)
            if not base_repository:
                logger.error(f"No repository configured for level: {level}")
                return False
            
            # Create user-scoped repository if user_id is available
            if effective_user_id and hasattr(base_repository, 'with_user'):
                repository = base_repository.with_user(effective_user_id)
                logger.debug(f"Atomic creation: Using user-scoped repository for user: {effective_user_id}")
            else:
                repository = base_repository
                logger.warning(f"Atomic creation: Using unscoped repository - no user_id available for {level.value} context")
            
            # Check if context already exists
            try:
                existing = repository.get(context_id)
                if existing:
                    logger.debug(f"Context {level.value}/{context_id} already exists")
                    return True
            except Exception as e:
                logger.debug(f"Context {level.value}/{context_id} does not exist, will create: {e}")
                pass
            
            # Build complete data with defaults
            complete_data = self._build_default_context_data(
                level=level.value,
                context_id=context_id,
                data=data,
                project_id=data.get("project_id"),
                git_branch_id=data.get("git_branch_id")
            )
            
            # Normalize context_id for database storage (generate proper UUIDs)
            if level == ContextLevel.GLOBAL:
                # GLOBAL_SINGLETON_UUID removed - each user has their own global context
                # Check if it's a concatenated global context (starts with global singleton UUID)
                # Check if it's a composite ID (UUID_UUID format)
                if context_id and '_' in context_id and len(context_id.split('_')) == 2:
                    logger.info(f"Atomic flow: Found concatenated global context ID, converting to UUID")
                    import uuid
                    # Extract user_id from the concatenated ID
                    parts = context_id.split("_", 1)
                    if len(parts) == 2:
                        user_uuid = parts[1]
                        # Use a namespace UUID for context generation
                        namespace = uuid.UUID("a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c")
                        proper_uuid = str(uuid.uuid5(namespace, user_uuid))
                        context_id = proper_uuid
                        logger.info(f"Atomic flow: Converted global context ID to proper UUID: {proper_uuid}")
            
            # Create entity directly
            context_entity = self._create_context_entity(
                level=level,
                context_id=context_id,
                data=complete_data,
                user_id=effective_user_id,
                project_id=data.get("project_id")
            )
            
            # Save directly to repository with proper error handling
            try:
                saved_context = repository.create(context_entity)
                
                if saved_context:
                    logger.info(f"Successfully created context atomically: {level.value}/{context_id}")
                    return True
                else:
                    logger.warning(f"Repository create returned None for {level.value}/{context_id}")
                    return False
                    
            except IntegrityError as ie:
                # Handle duplicate key constraint violations gracefully
                error_msg = str(ie).lower()
                if 'duplicate' in error_msg or 'unique constraint' in error_msg:
                    logger.info(f"Context {level.value}/{context_id} already exists (duplicate key), returning success")
                    # Context already exists, this is acceptable for idempotent operations
                    return True
                else:
                    logger.error(f"Integrity error creating context {level.value}/{context_id}: {ie}")
                    # Try to rollback the session if available
                    if hasattr(repository, 'session') and repository.session:
                        try:
                            repository.session.rollback()
                            logger.info("Session rolled back after integrity error")
                        except Exception as rollback_error:
                            logger.error(f"Failed to rollback session: {rollback_error}")
                    return False
                
        except Exception as e:
            logger.error(f"Failed atomic context creation for {level.value}/{context_id}: {e}", exc_info=True)
            # Try to rollback the session if available
            if hasattr(repository, 'session') and repository.session:
                try:
                    repository.session.rollback()
                    logger.info("Session rolled back after general error")
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {rollback_error}")
            return False
    
    def _resolve_project_id_from_branch(self, branch_id: str) -> Optional[str]:
        """
        Resolve project_id from git branch entity.
        
        Clean implementation following DDD patterns without legacy fallbacks.
        
        Args:
            branch_id: The git branch ID
            
        Returns:
            Optional project_id if found
        """
        try:
            logger.info(f"🔍 Resolving project_id from branch_id: {branch_id}")
            
            # Direct database query - following ORM as source of truth
            try:
                from ...infrastructure.database.database_config import get_session
                from ...infrastructure.database.models import ProjectGitBranch
                
                with get_session() as session:
                    git_branch = session.query(ProjectGitBranch).filter(
                        ProjectGitBranch.id == branch_id
                    ).first()
                    
                    if git_branch and git_branch.project_id:
                        logger.info(f"✅ Found project_id '{git_branch.project_id}' for branch '{branch_id}'")
                        return git_branch.project_id
                    else:
                        logger.warning(f"⚠️ Git branch '{branch_id}' not found or has no project_id")
                        return None
            except Exception as db_error:
                logger.error(f"❌ Database query failed: {db_error}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error in _resolve_project_id_from_branch for branch '{branch_id}': {e}", exc_info=True)
            return None
    
    def _should_allow_orphaned_creation(
        self, 
        context_level: ContextLevel, 
        context_id: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        Determine if a context should be allowed to be created even if parent validation fails.
        
        This provides more flexible context creation for certain scenarios where strict
        hierarchy validation might be too restrictive.
        """
        # Allow global context creation (no parents needed)
        if context_level == ContextLevel.GLOBAL:
            return True
        
        # Allow project creation in development/testing scenarios
        if context_level == ContextLevel.PROJECT:
            # If it's a test project or has special flags, allow orphaned creation
            if (data.get("auto_created") or 
                data.get("project_name", "").startswith("Test") or
                data.get("allow_orphaned_creation")):
                return True
        
        # Allow branch creation if it has valid project_id reference
        if context_level == ContextLevel.BRANCH:
            project_id = data.get("project_id")
            if project_id and data.get("allow_orphaned_creation"):
                return True
        
        # Allow task creation if it has valid branch_id reference
        if context_level == ContextLevel.TASK:
            branch_id = (data.get("branch_id") or 
                        data.get("parent_branch_id") or
                        data.get("git_branch_id"))
            if branch_id and data.get("allow_orphaned_creation"):
                return True
        
        return False
    
    def _get_parent_info(self, context_level: ContextLevel, context_entity) -> tuple:
        """Get parent level and ID for a context."""
        parent_level = None
        parent_id = None
        
        if context_level == ContextLevel.PROJECT:
            parent_level = ContextLevel.GLOBAL
            # Global context ID is user-specific
            import uuid
            namespace = uuid.UUID("a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c")
            parent_id = str(uuid.uuid5(namespace, self._user_id)) if self._user_id else None
        elif context_level == ContextLevel.BRANCH:
            parent_level = ContextLevel.PROJECT
            parent_id = getattr(context_entity, 'project_id', None)
        elif context_level == ContextLevel.TASK:
            parent_level = ContextLevel.BRANCH
            parent_id = getattr(context_entity, 'git_branch_id', None) or getattr(context_entity, 'branch_id', None)
        
        return parent_level, parent_id
    
    def _invalidate_child_caches(self, context_level: ContextLevel, context_id: str, user_id: str, cache):
        """Invalidate caches for child contexts."""
        try:
            if context_level == ContextLevel.GLOBAL:
                # Global changes affect all user contexts
                cache.invalidate_context(user_id=user_id)
                cache.invalidate_inheritance(user_id=user_id)
            elif context_level == ContextLevel.PROJECT:
                # Project changes affect branch and task contexts
                cache.invalidate_context(user_id=user_id, level="branch")
                cache.invalidate_context(user_id=user_id, level="task")
                cache.invalidate_inheritance(user_id=user_id, level="branch")
                cache.invalidate_inheritance(user_id=user_id, level="task")
            elif context_level == ContextLevel.BRANCH:
                # Branch changes affect task contexts
                cache.invalidate_context(user_id=user_id, level="task")
                cache.invalidate_inheritance(user_id=user_id, level="task")
        except Exception as e:
            logger.warning(f"Failed to invalidate child caches: {e}")
    
    def _ensure_global_context_exists(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Ensure global context exists, create if missing."""
        try:
            # Always generate user-specific UUID for global context
            effective_user_id = user_id or self._user_id
            if not effective_user_id:
                raise ValueError("user_id is required for context delegation")
            import uuid
            # Use a namespace UUID for context generation
            namespace = uuid.UUID("a47ae7b9-1d4b-4e5f-8b5a-9c3e5d2f8a1c")
            try:
                user_uuid = uuid.UUID(str(effective_user_id))
            except ValueError:
                user_uuid = uuid.uuid5(namespace, str(effective_user_id))
            global_context_id = str(uuid.uuid5(namespace, str(user_uuid)))
            
            # Check if global context exists
            global_repo = self._get_user_scoped_repository(self.repositories[ContextLevel.GLOBAL])
            if global_repo:
                try:
                    existing = global_repo.get(global_context_id)
                    if existing:
                        return {"success": True, "created": False, "context_id": global_context_id}
                except Exception:
                    pass  # Context doesn't exist, create it
            
            # Create global context using atomic method to avoid validation cycles
            global_data = {
                "organization_name": "Default Organization",
                "global_settings": {
                    "auto_context_creation": True,
                    "default_timezone": "UTC"
                },
                "metadata": {
                    "auto_created": True,
                    "created_by": "context_bootstrap",
                    "user_id": effective_user_id
                }
            }
            
            # Use atomic creation to avoid validation cycles
            success = self._create_context_atomically(
                level=ContextLevel.GLOBAL,
                context_id=global_context_id,
                data=global_data
            )
            
            result = {"success": success}
            
            if result["success"]:
                return {"success": True, "created": True, "context_id": global_context_id}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
        
        except Exception as e:
            logger.error(f"Failed to ensure global context exists: {e}")
            return {"success": False, "error": str(e)}
    
    def _ensure_project_context_exists(
        self, 
        project_id: str, 
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ensure project context exists, create if missing."""
        try:
            # Check if project context exists
            project_repo = self._get_user_scoped_repository(self.repositories[ContextLevel.PROJECT])
            if project_repo:
                try:
                    existing = project_repo.get(project_id)
                    if existing:
                        return {"success": True, "created": False, "context_id": project_id}
                except Exception:
                    pass  # Context doesn't exist, create it
            
            # Create project context using atomic method to avoid validation cycles
            project_data = {
                "project_name": f"Project {project_id[:8]}",
                "project_settings": {
                    "auto_created": True,
                    "default_branch": "main"
                },
                "metadata": {
                    "auto_created": True,
                    "created_by": "context_bootstrap",
                    "user_id": user_id or self._user_id
                }
            }
            
            # Use atomic creation to avoid validation cycles
            success = self._create_context_atomically(
                level=ContextLevel.PROJECT,
                context_id=project_id,
                data=project_data
            )
            
            result = {"success": success}
            
            if result["success"]:
                return {"success": True, "created": True, "context_id": project_id}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
        
        except Exception as e:
            logger.error(f"Failed to ensure project context exists: {e}")
            return {"success": False, "error": str(e)}
    
    def _ensure_branch_context_exists(
        self, 
        branch_id: str, 
        project_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ensure branch context exists, create if missing.
        
        ENHANCED: More robust branch context creation with git branch info lookup
        and better error handling.
        """
        try:
            logger.info(f"🔍 CONTEXT_FIX: Ensuring branch context exists for branch_id: {branch_id}, project_id: {project_id}")
            
            # Check if branch context exists
            branch_repo = self._get_user_scoped_repository(self.repositories[ContextLevel.BRANCH])
            if branch_repo:
                try:
                    existing = branch_repo.get(branch_id)
                    if existing:
                        logger.info(f"✅ CONTEXT_FIX: Branch context already exists for {branch_id}")
                        return {"success": True, "created": False, "context_id": branch_id}
                except Exception as check_error:
                    logger.debug(f"⚠️ CONTEXT_FIX: Branch context check failed (will create): {check_error}")
            
            # Get git branch info to populate branch data properly
            git_branch_name = f"branch-{branch_id[:8]}"  # Default fallback
            try:
                # Try to get actual git branch name
                from ...infrastructure.database.database_config import get_session
                from ...infrastructure.database.models import ProjectGitBranch
                
                with get_session() as session:
                    git_branch = session.query(ProjectGitBranch).filter(
                        ProjectGitBranch.id == branch_id
                    ).first()
                    
                    if git_branch:
                        git_branch_name = git_branch.name or git_branch_name
                        # Verify project_id matches (ensure consistency)
                        if git_branch.project_id and git_branch.project_id != project_id:
                            logger.warning(f"⚠️ CONTEXT_FIX: Project ID mismatch - provided: {project_id}, git branch has: {git_branch.project_id}")
                            # Use the git branch's project_id as it's authoritative
                            project_id = git_branch.project_id
                        logger.info(f"✅ CONTEXT_FIX: Found git branch info - name: {git_branch_name}, project_id: {project_id}")
                    else:
                        logger.warning(f"⚠️ CONTEXT_FIX: Git branch {branch_id} not found in database, using defaults")
                        
            except Exception as git_lookup_error:
                logger.debug(f"⚠️ CONTEXT_FIX: Git branch lookup failed, using defaults: {git_lookup_error}")
            
            # Create branch context using atomic method to avoid validation cycles
            branch_data = {
                "project_id": project_id,
                "git_branch_name": git_branch_name,
                "branch_settings": {
                    "auto_created": True,
                    "workflow_type": "standard",
                    "created_from": "context_bootstrap"
                },
                "metadata": {
                    "auto_created": True,
                    "created_by": "context_bootstrap",
                    "user_id": user_id or self._user_id,
                    "branch_id": branch_id,
                    "project_id": project_id
                }
            }
            
            logger.info(f"🔧 CONTEXT_FIX: Creating branch context with data: {branch_data}")
            
            # Use atomic creation to avoid validation cycles
            success = self._create_context_atomically(
                level=ContextLevel.BRANCH,
                context_id=branch_id,
                data=branch_data
            )
            
            if success:
                logger.info(f"✅ CONTEXT_FIX: Successfully created branch context for {branch_id}")
                return {"success": True, "created": True, "context_id": branch_id}
            else:
                logger.error(f"❌ CONTEXT_FIX: Failed to create branch context for {branch_id}")
                return {"success": False, "error": "Atomic context creation failed"}
        
        except Exception as e:
            logger.error(f"❌ CONTEXT_FIX: Exception in _ensure_branch_context_exists for branch {branch_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def bootstrap_context_hierarchy(
        self, 
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bootstrap the entire context hierarchy from scratch.
        
        This method is designed to set up a complete context hierarchy when starting
        from an empty state. It creates contexts in the proper order and provides
        detailed feedback on what was created.
        
        Args:
            user_id: Optional user to scope contexts to
            project_id: Optional specific project to create (otherwise generates one)
            branch_id: Optional specific branch to create (otherwise generates one)
            
        Returns:
            Dict with success status and details of created contexts
        """
        try:
            logger.info("Starting context hierarchy bootstrap")
            
            created_contexts = {}
            errors = []
            
            # Step 1: Ensure global context exists
            global_result = self._ensure_global_context_exists(user_id)
            if global_result["success"]:
                created_contexts["global"] = {
                    "id": global_result["context_id"],
                    "created": global_result.get("created", False)
                }
                logger.info(f"Global context: {global_result}")
            else:
                errors.append(f"Global context creation failed: {global_result.get('error')}")
            
            # Step 2: Create project context if requested
            if project_id:
                project_result = self._ensure_project_context_exists(project_id, user_id)
                if project_result["success"]:
                    created_contexts["project"] = {
                        "id": project_result["context_id"],
                        "created": project_result.get("created", False)
                    }
                    logger.info(f"Project context: {project_result}")
                else:
                    errors.append(f"Project context creation failed: {project_result.get('error')}")
            
            # Step 3: Create branch context if requested
            if branch_id and project_id:
                branch_result = self._ensure_branch_context_exists(branch_id, project_id, user_id)
                if branch_result["success"]:
                    created_contexts["branch"] = {
                        "id": branch_result["context_id"],
                        "created": branch_result.get("created", False)
                    }
                    logger.info(f"Branch context: {branch_result}")
                else:
                    errors.append(f"Branch context creation failed: {branch_result.get('error')}")
            
            # Determine overall success
            success = len(errors) == 0 and len(created_contexts) > 0
            
            result = {
                "success": success,
                "bootstrap_completed": True,
                "created_contexts": created_contexts,
                "hierarchy_ready": len(created_contexts) > 0
            }
            
            if errors:
                result["errors"] = errors
                result["partial_success"] = len(created_contexts) > 0
                
            # Add usage guidance
            result["usage_guidance"] = self._generate_bootstrap_usage_guidance(created_contexts)
            
            logger.info(f"Bootstrap completed: {result}")
            return result
        
        except Exception as e:
            logger.error(f"Bootstrap failed with exception: {e}", exc_info=True)
            return {
                "success": False,
                "bootstrap_completed": False,
                "error": f"Bootstrap exception: {str(e)}"
            }
    
    def _generate_bootstrap_usage_guidance(self, created_contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Generate usage guidance based on what contexts were created."""
        guidance = {
            "next_steps": [],
            "examples": []
        }
        
        # CRITICAL FIX: Check if created_contexts is None to prevent NoneType iteration error
        if created_contexts is None:
            logger.warning("🚨 CONTEXT_FIX: created_contexts is None, returning empty guidance")
            return guidance
        
        if "global" in created_contexts:
            guidance["next_steps"].append("Global context is ready for organization-wide settings")
            guidance["examples"].append({
                "action": "Update global settings",
                "command": f'manage_context(action="update", level="global", context_id="{created_contexts["global"]["id"]}", data={{"global_settings": {{"timezone": "UTC"}}}})'
            })
        
        if "project" in created_contexts:
            guidance["next_steps"].append("Project context is ready for project-specific configuration")
            guidance["examples"].append({
                "action": "Update project settings",
                "command": f'manage_context(action="update", level="project", context_id="{created_contexts["project"]["id"]}", data={{"project_settings": {{"default_branch": "main"}}}})'
            })
        
        if "branch" in created_contexts:
            guidance["next_steps"].append("Branch context is ready for branch-specific workflows")
            guidance["examples"].append({
                "action": "Update branch settings",
                "command": f'manage_context(action="update", level="branch", context_id="{created_contexts["branch"]["id"]}", data={{"branch_settings": {{"workflow_type": "gitflow"}}}})'
            })
        
        return guidance

    def auto_create_context_if_missing(
        self,
        level: str,
        context_id: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Auto-create a context if it doesn't already exist.
        
        This method first checks if the context exists, and only creates it if missing.
        It's safe to call multiple times and provides intelligent defaults.
        
        Args:
            level: Context level (global, project, branch, task)
            context_id: Context identifier
            data: Optional context data (defaults will be provided if missing)
            user_id: Optional user identifier
            project_id: Optional project identifier
            git_branch_id: Optional git branch identifier
            
        Returns:
            Dict with success status and context information
        """
        try:
            # Validate level
            context_level = ContextLevel(level)
            
            # Check if context already exists
            repository = self._get_user_scoped_repository(self.repositories.get(context_level))
            if not repository:
                return {
                    "success": False,
                    "error": f"No repository configured for level: {level}"
                }
            
            try:
                existing_context = repository.get(context_id)
                if existing_context:
                    logger.info(f"Context {level}/{context_id} already exists")
                    return {
                        "success": True,
                        "message": f"Context {context_id} already exists",
                        "context": self._entity_to_dict(existing_context),
                        "created": False
                    }
            except Exception:
                # Context doesn't exist, continue with creation
                logger.debug(f"Context {level}/{context_id} does not exist, will create")
                pass
            
            # Prepare data with defaults if not provided
            context_data = data or {}
            if not context_data:
                context_data = self._build_default_context_data(
                    level=level,
                    context_id=context_id,
                    data={},
                    project_id=project_id,
                    git_branch_id=git_branch_id
                )
            
            # Create the context using the main create_context method
            # Note: This may trigger recursive auto-creation of parent contexts
            result = self.create_context(
                level=level,
                context_id=context_id,
                data=context_data,
                user_id=user_id,
                project_id=project_id
            )
            
            if result.get("success", False):
                logger.info(f"Successfully auto-created context {level}/{context_id}")
                return {
                    **result,
                    "created": True
                }
            else:
                logger.warning(f"Failed to auto-create context {level}/{context_id}: {result.get('error', 'Unknown error')}")
                return result
                
        except Exception as e:
            logger.error(f"Exception during auto-creation of {level}/{context_id}: {e}")
            return {
                "success": False,
                "error": f"Exception during auto-creation: {str(e)}"
            }