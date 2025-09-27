"""
Git Branch Agent Handler

Handles agent assignment and management operations for git branches.
"""

import logging
from typing import Dict, Any, Optional
from .....application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class GitBranchAgentHandler:
    """Handler for git branch agent operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def assign_agent(self, facade: GitBranchApplicationFacade, project_id: str, 
                    git_branch_id: Optional[str], git_branch_name: Optional[str],
                    agent_id: str) -> Dict[str, Any]:
        """Assign an agent to a git branch."""
        
        try:
            # Determine git_branch_id if git_branch_name is provided
            if git_branch_name and not git_branch_id:
                branches_result = facade.list_git_branchs(project_id=project_id)
                git_branches = branches_result.get('git_branches', [])
                
                matching_branch = None
                for branch in git_branches:
                    if branch.get('git_branch_name') == git_branch_name:
                        matching_branch = branch
                        break
                
                if not matching_branch:
                    return self._response_formatter.create_error_response(
                        operation="assign_agent",
                        error=f"Git branch with name '{git_branch_name}' not found in project '{project_id}'",
                        error_code=ErrorCodes.RESOURCE_NOT_FOUND,
                        metadata={
                            "project_id": project_id,
                            "git_branch_name": git_branch_name,
                            "agent_id": agent_id,
                            "available_branches": [b.get('git_branch_name') for b in git_branches]
                        }
                    )
                
                git_branch_id = matching_branch.get('id')
            
            if not git_branch_id:
                return self._response_formatter.create_error_response(
                    operation="assign_agent",
                    error="Either git_branch_id or git_branch_name must be provided",
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    metadata={
                        "project_id": project_id,
                        "agent_id": agent_id
                    }
                )
            
            # Assign the agent
            result = facade.assign_agent(
                project_id=project_id,
                git_branch_id=git_branch_id,
                agent_id=agent_id
            )
            
            return self._response_formatter.create_success_response(
                operation="assign_agent",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "git_branch_name": git_branch_name,
                    "agent_id": agent_id,
                    "message": f"Agent '{agent_id}' assigned to git branch successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error assigning agent to git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="assign_agent",
                error=f"Failed to assign agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "git_branch_name": git_branch_name,
                    "agent_id": agent_id
                }
            )
    
    def unassign_agent(self, facade: GitBranchApplicationFacade, project_id: str, 
                      git_branch_id: Optional[str], git_branch_name: Optional[str],
                      agent_id: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch."""
        
        try:
            # Determine git_branch_id if git_branch_name is provided
            if git_branch_name and not git_branch_id:
                branches_result = facade.list_git_branchs(project_id=project_id)
                git_branches = branches_result.get('git_branches', [])
                
                matching_branch = None
                for branch in git_branches:
                    if branch.get('git_branch_name') == git_branch_name:
                        matching_branch = branch
                        break
                
                if not matching_branch:
                    return self._response_formatter.create_error_response(
                        operation="unassign_agent",
                        error=f"Git branch with name '{git_branch_name}' not found in project '{project_id}'",
                        error_code=ErrorCodes.RESOURCE_NOT_FOUND,
                        metadata={
                            "project_id": project_id,
                            "git_branch_name": git_branch_name,
                            "agent_id": agent_id,
                            "available_branches": [b.get('git_branch_name') for b in git_branches]
                        }
                    )
                
                git_branch_id = matching_branch.get('id')
            
            if not git_branch_id:
                return self._response_formatter.create_error_response(
                    operation="unassign_agent",
                    error="Either git_branch_id or git_branch_name must be provided",
                    error_code=ErrorCodes.VALIDATION_ERROR,
                    metadata={
                        "project_id": project_id,
                        "agent_id": agent_id
                    }
                )
            
            # Unassign the agent
            result = facade.unassign_agent(
                project_id=project_id,
                git_branch_id=git_branch_id,
                agent_id=agent_id
            )
            
            return self._response_formatter.create_success_response(
                operation="unassign_agent",
                data=result,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "git_branch_name": git_branch_name,
                    "agent_id": agent_id,
                    "message": f"Agent '{agent_id}' unassigned from git branch successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error unassigning agent from git branch: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="unassign_agent",
                error=f"Failed to unassign agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "git_branch_id": git_branch_id,
                    "git_branch_name": git_branch_name,
                    "agent_id": agent_id
                }
            )