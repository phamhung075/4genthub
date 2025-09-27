"""List Agents Use Case"""

import logging
from dataclasses import dataclass
from typing import List
from ...application.dtos.agent import AgentResponse
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import ProjectNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class ListAgentsRequest:
    """Request DTO for listing agents"""
    project_id: str


@dataclass
class ListAgentsResponse:
    """Response DTO for listing agents"""
    success: bool
    agents: List[AgentResponse] = None
    total_agents: int = 0
    error: str = None


class ListAgentsUseCase:
    """Use case for listing agents in a project"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def execute(self, request: ListAgentsRequest) -> ListAgentsResponse:
        """Execute the list agents use case"""
        try:
            # Execute domain operation
            result = self._agent_repository.list_agents(request.project_id)
            
            # Convert to response DTOs
            agents = [AgentResponse.from_dict(agent_data) for agent_data in result.get("agents", [])]
            
            return ListAgentsResponse(
                success=True,
                agents=agents,
                total_agents=result.get("total_agents", 0)
            )
            
        except ProjectNotFoundError as e:
            logger.warning(f"Project not found: {e}")
            return ListAgentsResponse(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in list agents: {e}")
            return ListAgentsResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )