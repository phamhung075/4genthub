"""Unregister Agent Use Case"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import AgentNotFoundError, ProjectNotFoundError

logger = logging.getLogger(__name__)


@dataclass
class UnregisterAgentRequest:
    """Request DTO for unregistering an agent"""
    project_id: str
    agent_id: str


@dataclass
class UnregisterAgentResponse:
    """Response DTO for agent unregistration"""
    success: bool
    agent_id: str
    agent_data: Dict[str, Any] = None
    removed_assignments: List[str] = None
    message: str = None
    error: str = None


class UnregisterAgentUseCase:
    """Use case for unregistering an agent"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def execute(self, request: UnregisterAgentRequest) -> UnregisterAgentResponse:
        """Execute the unregister agent use case"""
        try:
            # Execute domain operation
            result = self._agent_repository.unregister_agent(
                request.project_id,
                request.agent_id
            )
            
            return UnregisterAgentResponse(
                success=True,
                agent_id=request.agent_id,
                agent_data=result.get("agent_data"),
                removed_assignments=result.get("removed_assignments", []),
                message=f"Agent {request.agent_id} unregistered from project {request.project_id}"
            )
            
        except (AgentNotFoundError, ProjectNotFoundError) as e:
            logger.warning(f"Agent or project not found during unregistration: {e}")
            return UnregisterAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in unregister agent: {e}")
            return UnregisterAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=f"Unexpected error: {str(e)}"
            )