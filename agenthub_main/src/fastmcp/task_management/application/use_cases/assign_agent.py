"""Assign Agent Use Case"""

import logging
from dataclasses import dataclass
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.exceptions import AgentNotFoundError, ProjectNotFoundError
from ...domain.interfaces.repository_factory import IRepositoryFactory
from ...infrastructure.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


@dataclass
class AssignAgentRequest:
    """Request DTO for assigning an agent"""
    project_id: str
    agent_id: str
    git_branch_id: str


@dataclass
class AssignAgentResponse:
    """Response DTO for agent assignment"""
    success: bool
    agent_id: str
    git_branch_id: str = None
    message: str = None
    error: str = None


class AssignAgentUseCase:
    """Use case for assigning an agent to a task tree"""
    
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
        self._git_branch_repository = RepositoryFactory.get_git_branch_repository()
    
    
    def execute(self, request: AssignAgentRequest) -> AssignAgentResponse:
        """Execute the assign agent use case"""
        try:
            # Execute domain operation
            self._agent_repository.assign_agent_to_tree(
                request.project_id,
                request.agent_id,
                request.git_branch_id
            )
            
            return AssignAgentResponse(
                success=True,
                agent_id=request.agent_id,
                git_branch_id=request.git_branch_id,
                message=f"Agent {request.agent_id} assigned to tree {request.git_branch_id}"
            )
            
        except (AgentNotFoundError, ProjectNotFoundError) as e:
            logger.warning(f"Agent or project not found during assignment: {e}")
            return AssignAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in assign agent: {e}")
            return AssignAgentResponse(
                success=False,
                agent_id=request.agent_id,
                error=f"Unexpected error: {str(e)}"
            )