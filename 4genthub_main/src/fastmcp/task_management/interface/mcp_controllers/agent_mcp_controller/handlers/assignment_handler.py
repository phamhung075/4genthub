"""
Agent Assignment Handler

Handles agent assignment and unassignment operations to git branches.
"""

import logging
from typing import Dict, Any
from .....application.facades.agent_application_facade import AgentApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class AgentAssignmentHandler:
    """Handler for agent assignment operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def assign_agent(self, facade: AgentApplicationFacade, project_id: str,
                    agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Assign agent to a git branch."""
        
        try:
            result = facade.assign_agent(project_id, agent_id, git_branch_id)
            
            return self._response_formatter.create_success_response(
                operation="assign",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "git_branch_id": git_branch_id,
                    "success_message": "Agent assigned successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error assigning agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="assign",
                error=f"Failed to assign agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "git_branch_id": git_branch_id
                }
            )
    
    def unassign_agent(self, facade: AgentApplicationFacade, project_id: str,
                      agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Unassign agent from a git branch."""
        
        try:
            result = facade.unassign_agent(project_id, agent_id, git_branch_id)
            
            return self._response_formatter.create_success_response(
                operation="unassign",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "git_branch_id": git_branch_id,
                    "success_message": "Agent unassigned successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error unassigning agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="unassign",
                error=f"Failed to unassign agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "git_branch_id": git_branch_id
                }
            )