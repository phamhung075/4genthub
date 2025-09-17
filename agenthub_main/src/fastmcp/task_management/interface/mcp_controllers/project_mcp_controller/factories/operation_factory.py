"""
Project Operation Factory

Factory class that coordinates project operations by routing them to appropriate handlers.
"""

import logging
from typing import Dict, Any, Optional
from .....application.facades.project_application_facade import ProjectApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from ..handlers.crud_handler import ProjectCRUDHandler
from ..handlers.maintenance_handler import ProjectMaintenanceHandler

logger = logging.getLogger(__name__)


class ProjectOperationFactory:
    """Factory for coordinating project operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        
        # Initialize handlers
        self._crud_handler = ProjectCRUDHandler(response_formatter)
        self._maintenance_handler = ProjectMaintenanceHandler(response_formatter)
        
        logger.info("ProjectOperationFactory initialized with modular handlers")
    
    async def handle_operation(self, operation: str, facade: ProjectApplicationFacade, 
                        **kwargs) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        
        try:
            # CRUD Operations
            if operation in ["create", "get", "list", "update", "delete"]:
                return await self._handle_crud_operation(operation, facade, **kwargs)
            
            # Maintenance Operations
            elif operation in ["project_health_check", "cleanup_obsolete", 
                              "validate_integrity", "rebalance_agents"]:
                return await self._handle_maintenance_operation(operation, facade, **kwargs)
            
            else:
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code=ErrorCodes.INVALID_OPERATION,
                    metadata={"valid_operations": [
                        "create", "get", "list", "update", "delete",
                        "project_health_check", "cleanup_obsolete", 
                        "validate_integrity", "rebalance_agents"
                    ]}
                )
                
        except Exception as e:
            logger.error(f"Error in ProjectOperationFactory.handle_operation: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"operation": operation}
            )
    
    async def _handle_crud_operation(self, operation: str, facade: ProjectApplicationFacade, 
                              **kwargs) -> Dict[str, Any]:
        """Handle CRUD operations."""
        
        if operation == "create":
            return await self._crud_handler.create_project(
                facade=facade,
                name=kwargs.get('name'),
                description=kwargs.get('description'),
                user_id=kwargs.get('user_id')
            )
        
        elif operation == "get":
            return await self._crud_handler.get_project(
                facade=facade,
                project_id=kwargs.get('project_id'),
                name=kwargs.get('name')
            )
        
        elif operation == "list":
            return await self._crud_handler.list_projects(facade=facade)
        
        elif operation == "update":
            return await self._crud_handler.update_project(
                facade=facade,
                project_id=kwargs.get('project_id'),
                name=kwargs.get('name'),
                description=kwargs.get('description')
            )
        
        elif operation == "delete":
            return await self._crud_handler.delete_project(
                facade=facade,
                project_id=kwargs.get('project_id'),
                force=kwargs.get('force')
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported CRUD operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    async def _handle_maintenance_operation(self, operation: str, facade: ProjectApplicationFacade, 
                                    **kwargs) -> Dict[str, Any]:
        """Handle maintenance operations."""
        
        project_id = kwargs.get('project_id')
        force = kwargs.get('force', False)
        user_id = kwargs.get('user_id')
        
        if operation == "project_health_check":
            return await self._maintenance_handler.project_health_check(
                facade=facade,
                project_id=project_id,
                user_id=user_id
            )
        
        elif operation == "cleanup_obsolete":
            return await self._maintenance_handler.cleanup_obsolete(
                facade=facade,
                project_id=project_id,
                force=force,
                user_id=user_id
            )
        
        elif operation == "validate_integrity":
            return await self._maintenance_handler.validate_integrity(
                facade=facade,
                project_id=project_id,
                force=force,
                user_id=user_id
            )
        
        elif operation == "rebalance_agents":
            return await self._maintenance_handler.rebalance_agents(
                facade=facade,
                project_id=project_id,
                force=force,
                user_id=user_id
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported maintenance operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )