"""Agent Application Facade - Orchestrates agent-related use cases"""

import logging
from typing import Dict, Any
from dataclasses import asdict
from datetime import datetime

from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions.task_exceptions import AgentNotFoundError, ProjectNotFoundError
from ..use_cases.register_agent import RegisterAgentUseCase, RegisterAgentRequest
from ..use_cases.unregister_agent import UnregisterAgentUseCase, UnregisterAgentRequest
from ..use_cases.assign_agent import AssignAgentUseCase, AssignAgentRequest
from ..use_cases.unassign_agent import UnassignAgentUseCase, UnassignAgentRequest
from ..use_cases.get_agent import GetAgentUseCase, GetAgentRequest
from ..use_cases.list_agents import ListAgentsUseCase, ListAgentsRequest

logger = logging.getLogger(__name__)


class AgentApplicationFacade:
    """
    Application Facade that orchestrates agent-related use cases.
    Provides a unified interface for the Interface layer while maintaining
    proper DDD boundaries.
    
    This facade coordinates agent management operations through use cases
    and handles cross-cutting concerns like validation, error handling, 
    and response formatting at the application boundary.
    """
    
    def __init__(self, agent_repository: AgentRepository):
        """Initialize facade with required dependencies and use cases"""
        self._agent_repository = agent_repository
        
        # Initialize use cases
        self._register_agent_use_case = RegisterAgentUseCase(agent_repository)
        self._unregister_agent_use_case = UnregisterAgentUseCase(agent_repository)
        self._assign_agent_use_case = AssignAgentUseCase(agent_repository)
        self._unassign_agent_use_case = UnassignAgentUseCase(agent_repository)
        self._get_agent_use_case = GetAgentUseCase(agent_repository)
        self._list_agents_use_case = ListAgentsUseCase(agent_repository)
    
    def register_agent(self, project_id: str, agent_id: str = None, name: str = None, call_agent: str = None) -> Dict[str, Any]:
        """Register a new agent to a project"""
        try:
            # Create request DTO
            request = RegisterAgentRequest(
                project_id=project_id,
                agent_id=agent_id,
                name=name,
                call_agent=call_agent
            )
            
            # Execute use case
            response = self._register_agent_use_case.execute(request)
            
            if response.success:
                return {
                    "success": True,
                    "action": "register",
                    "agent": asdict(response.agent),
                    "message": response.message,
                    "hint": f"Agent '{name}' successfully registered and ready for assignment"
                }
            else:
                # Enhance error response with helpful guidance
                error_response = {
                    "success": False,
                    "action": "register",
                    "error": response.error,
                    "error_code": "REGISTRATION_FAILED"
                }
                
                # Add helpful hints based on error message
                if "already exists" in response.error.lower():
                    error_response["error_code"] = "DUPLICATE_AGENT"
                    error_response["hint"] = "Try using 'action=get' to view the existing agent or 'action=update' to modify it"
                    error_response["suggested_actions"] = [
                        {"action": "get", "agent_id": agent_id},
                        {"action": "update", "agent_id": agent_id},
                        {"action": "list", "project_id": project_id}
                    ]
                elif "project" in response.error.lower() and "not exist" in response.error.lower():
                    error_response["error_code"] = "PROJECT_NOT_FOUND"
                    error_response["hint"] = "Check that the project_id is correct or create the project first"
                    
                return error_response
                
        except ValueError as e:
            logger.warning(f"Validation error in register_agent: {e}")
            error_msg = str(e)
            response = {
                "success": False,
                "action": "register",
                "error": error_msg,
                "error_code": "VALIDATION_ERROR"
            }
            
            # Add specific hints for common validation errors
            if "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                response["error_code"] = "DUPLICATE_AGENT"
                response["hint"] = "An agent with this ID or name already exists. Consider using the existing agent."
                response["suggested_actions"] = [
                    {"action": "list", "project_id": project_id, "description": "List all agents in the project"},
                    {"action": "get", "agent_id": agent_id, "description": "Get details of the existing agent"}
                ]
            elif "required" in error_msg.lower() or "missing" in error_msg.lower():
                response["error_code"] = "MISSING_FIELD"
                response["hint"] = "Ensure all required fields (project_id, agent_id, name) are provided"
                
            return response
            
        except Exception as e:
            logger.error(f"Unexpected error in register_agent: {e}")
            return {
                "success": False,
                "action": "register",
                "error": f"Unexpected error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
                "hint": "An unexpected error occurred. Please check the logs or try again."
            }
    
    def unregister_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Unregister an agent from a project"""
        try:
            # Create request DTO
            request = UnregisterAgentRequest(
                project_id=project_id,
                agent_id=agent_id
            )
            
            # Execute use case
            response = self._unregister_agent_use_case.execute(request)
            
            if response.success:
                return {
                    "success": True,
                    "action": "unregister",
                    "agent_id": response.agent_id,
                    "agent_data": response.agent_data,
                    "removed_assignments": response.removed_assignments,
                    "message": response.message
                }
            else:
                return {
                    "success": False,
                    "action": "unregister",
                    "error": response.error
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in unregister_agent: {e}")
            return {"success": False, "action": "unregister", "error": f"Unexpected error: {str(e)}"}
    
    def assign_agent(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Assign an agent to a task tree"""
        logger.debug(f"[FACADE] assign_agent called with project_id={project_id}, agent_id={agent_id}, git_branch_id={git_branch_id}")
        logger.debug(f"[FACADE] Type of git_branch_id: {type(git_branch_id)}")
        
        try:
            # Create request DTO
            request = AssignAgentRequest(
                project_id=project_id,
                agent_id=agent_id,
                git_branch_id=git_branch_id
            )
            
            logger.debug(f"[FACADE] Created AssignAgentRequest, about to execute use case")
            
            # Execute use case
            response = self._assign_agent_use_case.execute(request)
            
            if response.success:
                return {
                    "success": True,
                    "action": "assign",
                    "agent_id": response.agent_id,
                    "git_branch_id": response.git_branch_id,
                    "message": response.message,
                    "metadata": {
                        "project_id": project_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "action": "assign",
                    "error": response.error,
                    "metadata": {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "git_branch_id": git_branch_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in assign_agent: {e}")
            return {"success": False, "action": "assign", "error": f"Unexpected error in assigning agent: {str(e)}", "metadata": {"project_id": project_id, "agent_id": agent_id, "git_branch_id": git_branch_id, "timestamp": datetime.now().isoformat()}}
    
    def unassign_agent(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """
        Unassigns an agent from a specific task tree within a project.
        
        Args:
            project_id: The ID of the project.
            agent_id: The ID of the agent to unassign.
            git_branch_id: The ID of the task tree (branch) from which to unassign the agent.
        
        Returns:
            Dict with the result of the unassignment operation.
        """
        try:
            # Use the use case to handle the business logic
            request = UnassignAgentRequest(project_id=project_id, agent_id=agent_id, git_branch_id=git_branch_id)
            response = self._unassign_agent_use_case.execute(request)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error in unassign_agent facade: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Get agent details"""
        try:
            # Create request DTO
            request = GetAgentRequest(
                project_id=project_id,
                agent_id=agent_id
            )
            
            # Execute use case
            response = self._get_agent_use_case.execute(request)
            
            if response.success:
                return {
                    "success": True,
                    "action": "get",
                    "agent": asdict(response.agent),
                    "workload_status": response.workload_status,
                    "metadata": {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "action": "get",
                    "error": response.error,
                    "metadata": {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in get_agent: {e}")
            return {"success": False, "action": "get", "error": f"Unexpected error in retrieving agent details: {str(e)}", "metadata": {"project_id": project_id, "agent_id": agent_id, "timestamp": datetime.now().isoformat()}}
    
    def list_agents(self, project_id: str) -> Dict[str, Any]:
        """List all agents in a project"""
        try:
            # Create request DTO
            request = ListAgentsRequest(
                project_id=project_id
            )
            
            # Execute use case
            response = self._list_agents_use_case.execute(request)
            
            if response.success:
                return {
                    "success": True,
                    "action": "list",
                    "agents": [asdict(agent) for agent in response.agents],
                    "metadata": {
                        "project_id": project_id,
                        "timestamp": datetime.now().isoformat(),
                        "count": len(response.agents)
                    }
                }
            else:
                return {
                    "success": False,
                    "action": "list",
                    "error": response.error,
                    "metadata": {
                        "project_id": project_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
        except Exception as e:
            logger.error(f"Unexpected error in list_agents: {e}")
            return {"success": False, "action": "list", "error": f"Unexpected error in listing agents: {str(e)}", "metadata": {"project_id": project_id, "timestamp": datetime.now().isoformat()}}
    
    def update_agent(self, project_id: str, agent_id: str, name: str = None, call_agent: str = None) -> Dict[str, Any]:
        """Update agent information"""
        try:
            # Create request DTO - using a direct repository call since use case might not be fully defined yet
            updated_agent = self._agent_repository.update_agent(project_id, agent_id, name, call_agent)
            return {
                "success": True,
                "action": "update",
                "agent": updated_agent,
                "message": f"Agent {agent_id} updated successfully",
                "metadata": {
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except AgentNotFoundError as e:
            logger.warning(f"Agent not found during update: {e}")
            return {"success": False, "action": "update", "error": str(e), "metadata": {"project_id": project_id, "agent_id": agent_id, "timestamp": datetime.now().isoformat()}}
        except ProjectNotFoundError as e:
            logger.warning(f"Project not found during update: {e}")
            return {"success": False, "action": "update", "error": str(e), "metadata": {"project_id": project_id, "agent_id": agent_id, "timestamp": datetime.now().isoformat()}}
        except Exception as e:
            logger.error(f"Unexpected error in update_agent: {e}")
            return {"success": False, "action": "update", "error": f"Unexpected error in updating agent: {str(e)}", "metadata": {"project_id": project_id, "agent_id": agent_id, "timestamp": datetime.now().isoformat()}}
    
    def rebalance_agents(self, project_id: str) -> Dict[str, Any]:
        """Rebalance agent assignments"""
        try:
            # Direct repository call since use case might not be fully defined yet
            result = self._agent_repository.rebalance_agents(project_id)
            return {
                "success": True,
                "action": "rebalance",
                "project_id": project_id,
                "rebalance_result": result.get("rebalance_result"),
                "message": f"Agent rebalancing completed for project {project_id}",
                "metadata": {
                    "project_id": project_id,
                    "timestamp": datetime.now().isoformat()
                }
            }
        except ProjectNotFoundError as e:
            logger.warning(f"Project not found during rebalance: {e}")
            return {"success": False, "action": "rebalance", "error": str(e), "metadata": {"project_id": project_id, "timestamp": datetime.now().isoformat()}}
        except Exception as e:
            logger.error(f"Unexpected error in rebalance_agents: {e}")
            return {"success": False, "action": "rebalance", "error": f"Unexpected error in rebalancing agents: {str(e)}", "metadata": {"project_id": project_id, "timestamp": datetime.now().isoformat()}}