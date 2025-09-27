"""
Git Branch Advanced Handler

Handles advanced operations like statistics, archiving, and restoration.
"""

import logging
from typing import Dict, Any
from .....application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class GitBranchAdvancedHandler:
    """Handler for advanced git branch operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def get_statistics(self, facade: GitBranchApplicationFacade, 
                      project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a git branch."""
        
        try:
            result = facade.get_statistics(
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            return self._response_formatter.create_success_response(
                operation="get_statistics",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "message": "Git branch statistics retrieved successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting git branch statistics: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="get_statistics",
                error=f"Failed to get statistics: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id
                }
            )
    
    def archive_git_branch(self, facade: GitBranchApplicationFacade, 
                          project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch."""
        
        try:
            result = facade.archive_git_branch(
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            return self._response_formatter.create_success_response(
                operation="archive",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "archived": True,
                    "message": "Git branch archived successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error archiving git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="archive",
                error=f"Failed to archive git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id
                }
            )
    
    def restore_git_branch(self, facade: GitBranchApplicationFacade, 
                          project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch."""
        
        try:
            result = facade.restore_git_branch(
                project_id=project_id,
                git_branch_id=git_branch_id
            )
            
            return self._response_formatter.create_success_response(
                operation="restore",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "restored": True,
                    "message": "Git branch restored successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error restoring git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="restore",
                error=f"Failed to restore git branch: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id
                }
            )