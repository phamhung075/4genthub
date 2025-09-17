"""Register Agent Use Case"""

import logging
from ...application.dtos.agent import (
    RegisterAgentRequest,
    RegisterAgentResponse,
    AgentResponse
)
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import ProjectNotFoundError
from ...domain.entities.agent import Agent

logger = logging.getLogger(__name__)


class RegisterAgentUseCase:
    """Use case for registering an agent"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def execute(self, request: RegisterAgentRequest) -> RegisterAgentResponse:
        """Execute the register agent use case"""
        try:
            # Create Agent entity with the provided information
            agent = Agent(
                id=request.agent_id,
                name=request.name,
                description=request.call_agent or "",  # Using call_agent as description
            )
            
            # Add the project to agent's assigned projects
            agent.assign_to_project(request.project_id)
            
            # Execute domain operation - pass the Agent entity
            result = self._agent_repository.register_agent(agent)
            
            # Convert AgentEntity to response DTO
            agent_dict = {
                "id": result.id,
                "name": result.name,
                "call_agent": result.description,  # Using description as call_agent
                "assignments": list(result.assigned_trees) if result.assigned_trees else []
            }
                
            agent_response = AgentResponse.from_dict(agent_dict)
            return RegisterAgentResponse.success_response(
                agent_response,
                f"Agent {request.agent_id} registered successfully to project {request.project_id}"
            )
            
        except ProjectNotFoundError as e:
            logger.warning(f"Project not found during agent registration: {e}")
            return RegisterAgentResponse.error_response(str(e))
        except ValueError as e:
            logger.warning(f"Validation error in register agent: {e}")
            return RegisterAgentResponse.error_response(str(e))
        except Exception as e:
            logger.error(f"Unexpected error in register agent: {e}")
            return RegisterAgentResponse.error_response(f"Unexpected error: {str(e)}")