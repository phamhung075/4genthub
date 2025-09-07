"""
Agent CRUD Handler

Handles basic CRUD operations for agent management.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from .....application.facades.agent_application_facade import AgentApplicationFacade
from ....utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes

logger = logging.getLogger(__name__)


class AgentCRUDHandler:
    """Handler for agent CRUD operations."""
    
    def __init__(self, response_formatter: StandardResponseFormatter):
        self._response_formatter = response_formatter
    
    def register_agent(self, facade: AgentApplicationFacade, project_id: str, 
                      agent_id: Optional[str], name: str, call_agent: Optional[str]) -> Dict[str, Any]:
        """Register a new agent."""
        
        try:
            # Auto-generate agent_id if not provided
            if not agent_id:
                agent_id = str(uuid.uuid4())
            
            result = facade.register_agent(project_id, agent_id, name, call_agent)
            
            return self._response_formatter.create_success_response(
                operation="register",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "agent_name": name,
                    "success_message": f"Agent '{name}' registered successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error registering agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="register",
                error=f"Failed to register agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id, "agent_name": name}
            )
    
    def get_agent(self, facade: AgentApplicationFacade, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Get agent details."""
        
        try:
            result = facade.get_agent(project_id, agent_id)
            
            return self._response_formatter.create_success_response(
                operation="get",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "success_message": "Agent retrieved successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="get",
                error=f"Failed to retrieve agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id, "agent_id": agent_id}
            )
    
    def list_agents(self, facade: AgentApplicationFacade, project_id: str) -> Dict[str, Any]:
        """List all agents in project."""
        
        try:
            result = facade.list_agents(project_id)
            
            agent_count = len(result.get('agents', []))
            return self._response_formatter.create_success_response(
                operation="list",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_count": agent_count,
                    "success_message": f"Retrieved {agent_count} agents"
                }
            )
            
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="list",
                error=f"Failed to list agents: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id}
            )
    
    def update_agent(self, facade: AgentApplicationFacade, project_id: str,
                    agent_id: str, name: Optional[str], call_agent: Optional[str]) -> Dict[str, Any]:
        """Update an existing agent."""
        
        try:
            result = facade.update_agent(project_id, agent_id, name, call_agent)
            
            return self._response_formatter.create_success_response(
                operation="update",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "updated_name": name,
                    "success_message": "Agent updated successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="update",
                error=f"Failed to update agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id, "agent_id": agent_id}
            )
    
    def unregister_agent(self, facade: AgentApplicationFacade, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Unregister an agent."""
        
        try:
            result = facade.unregister_agent(project_id, agent_id)
            
            return self._response_formatter.create_success_response(
                operation="unregister",
                data=result,
                metadata={
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "success_message": "Agent unregistered successfully"
                }
            )
            
        except Exception as e:
            logger.error(f"Error unregistering agent: {str(e)}")
            return self._response_formatter.create_error_response(
                operation="unregister",
                error=f"Failed to unregister agent: {str(e)}",
                error_code=ErrorCodes.OPERATION_FAILED,
                metadata={"project_id": project_id, "agent_id": agent_id}
            )