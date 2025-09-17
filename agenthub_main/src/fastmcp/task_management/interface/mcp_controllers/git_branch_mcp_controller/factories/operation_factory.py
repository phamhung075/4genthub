"""
Git Branch Operation Factory

Factory class that coordinates git branch operations by routing them to appropriate handlers.
"""

import logging
from typing import Dict, Any, Optional
from .....application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ErrorCodes
from ..handlers.crud_handler import GitBranchCRUDHandler
from ..handlers.agent_handler import GitBranchAgentHandler
from ..handlers.advanced_handler import GitBranchAdvancedHandler

logger = logging.getLogger(__name__)


class GitBranchOperationFactory:
    """Factory for coordinating git branch operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
        
        # Initialize handlers
        self._crud_handler = GitBranchCRUDHandler(response_formatter)
        self._agent_handler = GitBranchAgentHandler(response_formatter)
        self._advanced_handler = GitBranchAdvancedHandler(response_formatter)
        
        logger.info("GitBranchOperationFactory initialized with modular handlers")
    
    def handle_operation(self, operation: str, facade: GitBranchApplicationFacade, 
                        **kwargs) -> Dict[str, Any]:
        """Route operation to appropriate handler."""
        
        try:
            # CRUD Operations
            if operation == "create":
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation == "update":
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation == "get":
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation == "delete":
                return self._handle_crud_operation(operation, facade, **kwargs)
            elif operation == "list":
                return self._handle_crud_operation(operation, facade, **kwargs)
            
            # Agent Operations
            elif operation == "assign_agent":
                return self._handle_agent_operation(operation, facade, **kwargs)
            elif operation == "unassign_agent":
                return self._handle_agent_operation(operation, facade, **kwargs)
            
            # Advanced Operations
            elif operation == "get_statistics":
                return self._handle_advanced_operation(operation, facade, **kwargs)
            elif operation == "archive":
                return self._handle_advanced_operation(operation, facade, **kwargs)
            elif operation == "restore":
                return self._handle_advanced_operation(operation, facade, **kwargs)
            
            else:
                return self._response_formatter.create_error_response(
                    operation=operation,
                    error=f"Unknown operation: {operation}",
                    error_code=ErrorCodes.INVALID_OPERATION,
                    metadata={"valid_operations": [
                        "create", "update", "get", "delete", "list",
                        "assign_agent", "unassign_agent", 
                        "get_statistics", "archive", "restore"
                    ]}
                )
                
        except Exception as e:
            logger.error(f"Error in GitBranchOperationFactory.handle_operation: {str(e)}")
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Operation failed: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"operation": operation}
            )
    
    def _handle_crud_operation(self, operation: str, facade: GitBranchApplicationFacade, 
                              **kwargs) -> Dict[str, Any]:
        """Handle CRUD operations."""
        
        if operation == "create":
            return self._crud_handler.create_git_branch(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_name=kwargs.get('git_branch_name'),
                git_branch_description=kwargs.get('git_branch_description')
            )
        
        elif operation == "update":
            return self._crud_handler.update_git_branch(
                facade=facade,
                git_branch_id=kwargs.get('git_branch_id'),
                project_id=kwargs.get('project_id'),
                git_branch_name=kwargs.get('git_branch_name'),
                git_branch_description=kwargs.get('git_branch_description')
            )
        
        elif operation == "get":
            return self._crud_handler.get_git_branch(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id')
            )
        
        elif operation == "delete":
            return self._crud_handler.delete_git_branch(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id')
            )
        
        elif operation == "list":
            return self._crud_handler.list_git_branches(
                facade=facade,
                project_id=kwargs.get('project_id')
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported CRUD operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    def _handle_agent_operation(self, operation: str, facade: GitBranchApplicationFacade, 
                               **kwargs) -> Dict[str, Any]:
        """Handle agent operations."""
        
        if operation == "assign_agent":
            return self._agent_handler.assign_agent(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id'),
                git_branch_name=kwargs.get('git_branch_name'),
                agent_id=kwargs.get('agent_id')
            )
        
        elif operation == "unassign_agent":
            return self._agent_handler.unassign_agent(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id'),
                git_branch_name=kwargs.get('git_branch_name'),
                agent_id=kwargs.get('agent_id')
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported agent operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )
    
    def _handle_advanced_operation(self, operation: str, facade: GitBranchApplicationFacade, 
                                  **kwargs) -> Dict[str, Any]:
        """Handle advanced operations."""
        
        if operation == "get_statistics":
            return self._advanced_handler.get_statistics(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id')
            )
        
        elif operation == "archive":
            return self._advanced_handler.archive_git_branch(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id')
            )
        
        elif operation == "restore":
            return self._advanced_handler.restore_git_branch(
                facade=facade,
                project_id=kwargs.get('project_id'),
                git_branch_id=kwargs.get('git_branch_id')
            )
        
        else:
            return self._response_formatter.create_error_response(
                operation=operation,
                error=f"Unsupported advanced operation: {operation}",
                error_code=ErrorCodes.INVALID_OPERATION
            )