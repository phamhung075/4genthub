"""Register Agent Use Case"""

import logging
from ...application.dtos.agent import (
    RegisterAgentRequest,
    RegisterAgentResponse,
    AgentResponse
)
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import ProjectNotFoundError

logger = logging.getLogger(__name__)


class RegisterAgentUseCase:
    """Use case for registering an agent"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def execute(self, request: RegisterAgentRequest) -> RegisterAgentResponse:
        """Execute the register agent use case"""
        try:
            # Execute domain operation
            result = self._agent_repository.register_agent(
                request.project_id,
                request.agent_id,
                request.name,
                request.call_agent
            )
            
            # Convert to response DTO
            agent_response = AgentResponse.from_dict(result)
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