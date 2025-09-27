"""Unassign Agent Use Case"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import AgentNotFoundError, ProjectNotFoundError
from ...domain.interfaces.repository_factory import IRepositoryFactory
from ...infrastructure.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


@dataclass
class UnassignAgentRequest:
    """Request DTO for unassigning an agent"""
    project_id: str
    agent_id: str
    git_branch_id: Optional[str] = None


@dataclass
class UnassignAgentResponse:
    """Response DTO for agent unassignment"""
    success: bool
    agent_id: str
    removed_assignments: List[str] = None
    remaining_assignments: List[str] = None
    message: str = None
    error: str = None
    
    def to_dict(self) -> dict:
        """Convert response to dictionary"""
        result = {
            "success": self.success,
            "agent_id": self.agent_id
        }
        if self.removed_assignments is not None:
            result["removed_assignments"] = self.removed_assignments
        if self.remaining_assignments is not None:
            result["remaining_assignments"] = self.remaining_assignments
        if self.message:
            result["message"] = self.message
        if self.error:
            result["error"] = self.error
        return result


class UnassignAgentUseCase:
    """Use case for unassigning an agent from task tree(s)"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
        self._git_branch_repository = RepositoryFactory.get_git_branch_repository()
    
    
    def execute(self, request: UnassignAgentRequest) -> UnassignAgentResponse:
        """Execute the unassign agent use case"""
        try:
            # Execute domain operation
            result = self._agent_repository.unassign_agent_from_tree(
                request.project_id,
                request.agent_id,
                request.git_branch_id
            )
            
            removed_count = len(result.get("removed_assignments", []))
            return UnassignAgentResponse(
                success=True,
                agent_id=request.agent_id,
                removed_assignments=result.get("removed_assignments", []),
                remaining_assignments=result.get("remaining_assignments", []),
                message=f"Agent {request.agent_id} unassigned from {removed_count} tree(s)"
            )
            
        except (AgentNotFoundError, ProjectNotFoundError) as e:
            logger.warning(f"Agent or project not found during unassignment: {e}")
            return UnassignAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in unassign agent: {e}")
            return UnassignAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=f"Unexpected error: {str(e)}"
            )