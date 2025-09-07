"""
Base User-Scoped Repository for Data Isolation

This module provides a base repository class that automatically handles
user-based data isolation for all derived repositories.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class BaseUserScopedRepository:
    """
    Base repository that automatically scopes all operations to a specific user.
    
    This ensures data isolation by automatically adding user_id filters to all
    database queries and setting user_id on all created entities.
    """
    
    def __init__(self, session: Session, user_id: Optional[str] = None):
        """
        Initialize the repository with a database session and user context.
        
        Args:
            session: SQLAlchemy database session
            user_id: ID of the user whose data should be accessed.
                    If None, operates in system/admin mode (use with caution)
        """
        self.session = session
        self.user_id = user_id
        
        # When user_id is None, operate in system mode (no user filtering)
        self._is_system_mode = user_id is None
        
        if self._is_system_mode:
            logger.info("Repository initialized in system mode during startup - no user filtering applied (expected behavior)")
    
    def with_user(self, user_id: str) -> 'BaseUserScopedRepository':
        """
        Create a new instance of this repository scoped to a specific user.
        
        Args:
            user_id: ID of the user to scope operations to
            
        Returns:
            New repository instance scoped to the user
        """
        # For repositories that expect session_factory as first parameter, use it
        if hasattr(self, 'session_factory') and self.session_factory:
            new_repo = self.__class__(self.session_factory, user_id)
        else:
            # For repositories that expect session as first parameter
            new_repo = self.__class__(self.session, user_id)
        
        # Preserve session_factory if it exists
        if hasattr(self, 'session_factory'):
            new_repo.session_factory = self.session_factory
            
        return new_repo
    
    def get_user_filter(self) -> Dict[str, Any]:
        """
        Get the filter dictionary for user-scoped queries.
        
        Returns:
            Dictionary with user_id filter, or empty dict in system mode
        """
        if self._is_system_mode:
            return {}
        return {"user_id": self.user_id}
    
    def apply_user_filter(self, query):
        """
        Apply user filtering to a SQLAlchemy query or SQL string.
        
        Args:
            query: SQLAlchemy query object or SQL string
            
        Returns:
            Query with user filter applied
        """
        if self._is_system_mode:
            return query
        
        # Handle string queries (raw SQL)
        if isinstance(query, str):
            if "WHERE" in query.upper():
                return f"{query} AND user_id = '{self.user_id}'"
            else:
                return f"{query} WHERE user_id = '{self.user_id}'"
        
        # Handle SQLAlchemy query objects
        try:
            # Check if the model has user_id attribute
            if hasattr(query, 'column_descriptions'):
                model = query.column_descriptions[0]['entity']
                if hasattr(model, 'user_id'):
                    return query.filter(model.user_id == self.user_id)
                else:
                    logger.warning(f"Model {model.__name__} does not have user_id attribute")
                    return query
            else:
                # Fallback for other query types
                logger.warning("Query type not recognized, attempting generic filter")
                return query
        except (AttributeError, IndexError, KeyError) as e:
            logger.warning(f"Could not apply user filter: {e}")
            return query
    
    def ensure_user_ownership(self, entity) -> None:
        """
        Ensure an entity belongs to the current user.
        
        Args:
            entity: Entity to check
            
        Raises:
            PermissionError: If entity doesn't belong to the user
        """
        if self._is_system_mode:
            return
        
        if hasattr(entity, 'user_id'):
            if entity.user_id != self.user_id:
                raise PermissionError(f"Access denied: Entity does not belong to user {self.user_id}")
        else:
            logger.warning(f"Entity {type(entity).__name__} does not have user_id attribute")
    
    def set_user_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add user_id to data dictionary for entity creation.
        
        Args:
            data: Dictionary of entity data
            
        Returns:
            Data dictionary with user_id added
        """
        if not self._is_system_mode:
            data['user_id'] = self.user_id
            logger.debug(f"🚨 USER_ID_DEBUG: Setting user_id in data: {self.user_id}")
        else:
            # Authentication is required - no fallbacks
            logger.error(f"Repository in system mode - user authentication required")
            raise ValueError("User authentication required. No user ID provided.")
        return data
    
    def validate_bulk_operation(self, entities: List[Any]) -> None:
        """
        Validate that all entities in a bulk operation belong to the user.
        
        Args:
            entities: List of entities to validate
            
        Raises:
            PermissionError: If any entity doesn't belong to the user
        """
        if self._is_system_mode:
            return
        
        for entity in entities:
            self.ensure_user_ownership(entity)
    
    def create_system_context(self) -> 'BaseUserScopedRepository':
        """
        Create a system-level context for administrative operations.
        
        WARNING: This bypasses user isolation. Use only for system operations.
        
        Returns:
            Repository instance in system mode
        """
        logger.warning("Creating system context - user isolation bypassed")
        return self.__class__(self.session, user_id=None)
    
    def is_system_mode(self) -> bool:
        """
        Check if repository is operating in system mode.
        
        Returns:
            True if in system mode, False otherwise
        """
        return self._is_system_mode
    
    def get_current_user_id(self) -> Optional[str]:
        """
        Get the current user ID this repository is scoped to.
        
        Returns:
            User ID or None if in system mode
        """
        return self.user_id
    
    def log_access(self, operation: str, entity_type: str, entity_id: Optional[str] = None) -> None:
        """
        Log data access for audit purposes.
        
        Args:
            operation: Type of operation (create, read, update, delete)
            entity_type: Type of entity being accessed
            entity_id: ID of the entity (if applicable)
        """
        if self.user_id:
            logger.info(f"User {self.user_id} performed {operation} on {entity_type} {entity_id or 'new'}")
        else:
            logger.info(f"System performed {operation} on {entity_type} {entity_id or 'new'}")


class UserScopedError(Exception):
    """Exception raised when user-scoped operation fails"""
    pass


class InsufficientPermissionsError(UserScopedError):
    """Exception raised when user lacks permissions for an operation"""
    pass


class CrossUserAccessError(UserScopedError):
    """Exception raised when user attempts to access another user's data"""
    pass