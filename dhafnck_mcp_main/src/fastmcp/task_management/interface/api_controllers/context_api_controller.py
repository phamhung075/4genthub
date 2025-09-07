"""
Context API Controller

This controller handles frontend context management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
from typing import Dict, Any, Optional

from ...application.facades.unified_context_facade import UnifiedContextFacade
from ...application.services.facade_service import FacadeService

logger = logging.getLogger(__name__)


class ContextAPIController:
    """
    API Controller for context management operations.
    
    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    """
    
    def __init__(self):
        """Initialize the controller"""
        self.facade_service = FacadeService.get_instance()
    
    def create_context(self, level: str, context_id: str, data: Dict[str, Any], user_id: str, session) -> Dict[str, Any]:
        """
        Create a new context.
        
        Args:
            level: Context level (global, project, branch, task)
            context_id: Context identifier
            data: Context data
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Context creation result
        """
        try:
            # Get unified context facade from service
            facade = self.facade_service.get_context_facade(user_id=user_id)
            
            # Prepare request parameters
            request_params = {
                "level": level,
                "context_id": context_id,
                "data": data,
                "user_id": user_id
            }
            
            # Delegate to facade
            result = facade.create_context(**request_params)
            
            logger.info(f"Context created successfully for user {user_id}: {level}/{context_id}")
            
            return {
                "success": True,
                "context": result.get("context"),
                "message": "Context created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating context for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create context"
            }
    
    def get_context(self, level: str, context_id: str, include_inherited: bool, user_id: str, session) -> Dict[str, Any]:
        """
        Get a context.
        
        Args:
            level: Context level
            context_id: Context identifier
            include_inherited: Whether to include inherited data
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Context data
        """
        try:
            # Get unified context facade from service
            facade = self.facade_service.get_context_facade(user_id=user_id)
            
            # Prepare request parameters
            request_params = {
                "level": level,
                "context_id": context_id,
                "include_inherited": include_inherited,
                "user_id": user_id
            }
            
            # Delegate to facade
            result = facade.get_context(**request_params)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Context not found",
                    "message": "Context not found or access denied"
                }
            
            logger.info(f"Retrieved context {level}/{context_id} for user {user_id}")
            
            return {
                "success": True,
                "context": result.get("context")
            }
            
        except Exception as e:
            logger.error(f"Error getting context {level}/{context_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get context"
            }
    
    def update_context(self, level: str, context_id: str, data: Dict[str, Any], user_id: str, session) -> Dict[str, Any]:
        """
        Update a context.
        
        Args:
            level: Context level
            context_id: Context identifier
            data: Updated context data
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Updated context data
        """
        try:
            # Get unified context facade from service
            facade = self.facade_service.get_context_facade(user_id=user_id)
            
            # Prepare request parameters
            request_params = {
                "level": level,
                "context_id": context_id,
                "data": data,
                "user_id": user_id
            }
            
            # Delegate to facade
            result = facade.update_context(**request_params)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Context not found",
                    "message": "Context not found or access denied"
                }
            
            logger.info(f"Updated context {level}/{context_id} for user {user_id}")
            
            return {
                "success": True,
                "context": result.get("context"),
                "message": "Context updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error updating context {level}/{context_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update context"
            }
    
    def delete_context(self, level: str, context_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Delete a context.
        
        Args:
            level: Context level
            context_id: Context identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Deletion result
        """
        try:
            # Get unified context facade from service
            facade = self.facade_service.get_context_facade(user_id=user_id)
            
            # Prepare request parameters
            request_params = {
                "level": level,
                "context_id": context_id,
                "user_id": user_id
            }
            
            # Delegate to facade
            result = facade.delete_context(**request_params)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Context not found",
                    "message": "Context not found or access denied"
                }
            
            logger.info(f"Deleted context {level}/{context_id} for user {user_id}")
            
            return {
                "success": True,
                "message": "Context deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting context {level}/{context_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to delete context"
            }
    
    def resolve_context(self, level: str, context_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Resolve a context with full inheritance chain.
        
        Args:
            level: Context level
            context_id: Context identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Resolved context data
        """
        try:
            # Get unified context facade from service
            facade = self.facade_service.get_context_facade(user_id=user_id)
            
            # Prepare request parameters
            request_params = {
                "level": level,
                "context_id": context_id,
                "user_id": user_id
            }
            
            # Delegate to facade
            result = facade.resolve_context(**request_params)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": "Context not found",
                    "message": "Context not found or access denied"
                }
            
            logger.info(f"Resolved context {level}/{context_id} for user {user_id}")
            
            return {
                "success": True,
                "context": result.get("context"),
                "inheritance_chain": result.get("inheritance_chain", [])
            }
            
        except Exception as e:
            logger.error(f"Error resolving context {level}/{context_id} for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to resolve context"
            }