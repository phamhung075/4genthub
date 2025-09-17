"""Get Agent Use Case"""

import logging
from dataclasses import dataclass
from ...application.dtos.agent import AgentResponse
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import AgentNotFoundError, ProjectNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class GetAgentRequest:
    """Request DTO for getting an agent"""
    project_id: str
    agent_id: str


@dataclass
class GetAgentResponse:
    """Response DTO for getting an agent"""
    success: bool
    agent: AgentResponse = None
    workload_status: str = None
    error: str = None


class GetAgentUseCase:
    """Use case for getting agent details"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def execute(self, request: GetAgentRequest) -> GetAgentResponse:
        """Execute the get agent use case"""
        try:
            # Execute domain operation
            agent_data = self._agent_repository.get_agent(
                request.project_id,
                request.agent_id
            )
            
            # Convert to response DTO
            agent_response = AgentResponse.from_dict(agent_data)
            
            return GetAgentResponse(
                success=True,
                agent=agent_response,
                workload_status="Available for assignment analysis"
            )
            
        except (AgentNotFoundError, ProjectNotFoundError) as e:
            logger.warning(f"Agent or project not found: {e}")
            return GetAgentResponse(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in get agent: {e}")
            return GetAgentResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )