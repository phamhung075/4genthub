"""
Git Branch CRUD Handler

Handles basic CRUD operations for git branch management.
"""

import logging
from typing import Dict, Any, Optional
from .....application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class GitBranchCRUDHandler:
    """Handler for git branch CRUD operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def create_git_branch(self, facade: GitBranchApplicationFacade, project_id: str, 
                         git_branch_name: str, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new git branch."""
        
        try:
            result = facade.create_git_branch(
                project_id=project_id,
                git_branch_name=git_branch_name,
                git_branch_description=git_branch_description
            )
            
            return self._response_formatter.create_success_response(
                operation="create",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_name": git_branch_name,
                    "message": f"Git branch '{git_branch_name}' created successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="create",
                error=f"Failed to create git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id, "git_branch_name": git_branch_name}
            )
    
    def update_git_branch(self, facade: GitBranchApplicationFacade, git_branch_id: str, 
                         project_id: str, git_branch_name: Optional[str] = None,
                         git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing git branch."""
        
        try:
            result = facade.update_git_branch(
                git_branch_id=git_branch_id,
                project_id=project_id,
                git_branch_name=git_branch_name,
                git_branch_description=git_branch_description
            )
            
            return self._response_formatter.create_success_response(
                operation="update",
                data=result,
                metadata={
                    "git_branch_id": git_branch_id,
                    "project_id": project_id,
                    "message": "Git branch updated successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="update",
                error=f"Failed to update git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"git_branch_id": git_branch_id, "project_id": project_id}
            )
    
    def get_git_branch(self, facade: GitBranchApplicationFacade, 
                      project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get a specific git branch."""
        
        try:
            result = facade.get_git_branch(
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            return self._response_formatter.create_success_response(
                operation="get",
                data=result,
                metadata={
                    "git_branch_id": git_branch_id,
                    "project_id": project_id,
                    "message": "Git branch retrieved successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="get",
                error=f"Failed to retrieve git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"git_branch_id": git_branch_id, "project_id": project_id}
            )
    
    def delete_git_branch(self, facade: GitBranchApplicationFacade, 
                         project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch."""
        
        try:
            result = facade.delete_git_branch(
                git_branch_id=git_branch_id,
                project_id=project_id
            )
            
            # Check if the deletion was successful
            if result and isinstance(result, dict) and not result.get("success", True):
                # Handle cases where the facade returns a failure response
                error_msg = result.get("error", "Failed to delete git branch")
                error_code = result.get("error_code", ErrorCodes.OPERATION_FAILED)
                return self._response_formatter.create_error_response(
                    operation="delete",
                    error=error_msg,
                    error_code=error_code,
                    metadata={"git_branch_id": git_branch_id, "project_id": project_id}
                )
            
            return self._response_formatter.create_success_response(
                operation="delete",
                data={"deleted": True},
                metadata={
                    "git_branch_id": git_branch_id,
                    "project_id": project_id,
                    "message": "Git branch deleted successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="delete",
                error=f"Failed to delete git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"git_branch_id": git_branch_id, "project_id": project_id}
            )
    
    def list_git_branches(self, facade: GitBranchApplicationFacade, 
                         project_id: str) -> Dict[str, Any]:
        """List all git branches for a project."""
        
        try:
            result = facade.list_git_branchs(project_id=project_id)
            
            return self._response_formatter.create_success_response(
                operation="list",
                data=result,
                metadata={
                    "project_id": project_id,
                    "message": f"Retrieved {len(result.get('git_branches', []))} git branches"
                }
            )
            
        except Exception as e:
            logger.error(f"Error listing git branches: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="list",
                error=f"Failed to list git branches: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id}
            )