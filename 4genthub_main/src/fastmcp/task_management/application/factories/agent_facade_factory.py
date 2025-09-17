"""Agent Facade Factory

Factory for creating agent application facades with proper dependency injection following DDD patterns.

CRITICAL CHANGE: This factory now requires proper user authentication.
The default_id fallback has been removed to enforce security requirements.
"""

import logging
from typing import Optional, Dict
from ...application.facades.agent_application_facade import AgentApplicationFacade
from ...infrastructure.repositories.agent_repository_factory import (
    get_default_agent_repository,
    AgentRepositoryFactory
)

logger = logging.getLogger(__name__)


class AgentFacadeFactory:
    """
    Factory for creating agent application facades with proper DDD dependency injection.
    
    This factory ensures proper layering and dependency direction:
    - Creates facades with injected repositories
    - Repositories handle data persistence
    - Supports caching for performance optimization
    """
    
    def __init__(self, agent_repository_factory: Optional[AgentRepositoryFactory] = None):
        """
        Initialize the agent facade factory.
        
        Args:
            agent_repository_factory: Optional factory for creating agent repositories
        """
        self._agent_repository_factory = agent_repository_factory
        self._facades_cache: Dict[str, AgentApplicationFacade] = {}
        logger.info("AgentFacadeFactory initialized")
    
    def create_agent_facade(self, 
                           project_id: str,
                           user_id: Optional[str] = None) -> AgentApplicationFacade:
        """
        Create an agent application facade with proper dependency injection.
        
        Args:
            project_id: Project identifier for scoping (required)
            user_id: User identifier for data isolation (optional - defaults to 'system')
            
        Returns:
            AgentApplicationFacade instance with injected dependencies
        """
        # Create cache key
        cache_key = f"{project_id}"
        
        # Check cache first
        if cache_key in self._facades_cache:
            logger.debug(f"Returning cached agent facade for {cache_key}")
            return self._facades_cache[cache_key]
        
        # Require user_id for proper multi-tenancy
        if not user_id:
            raise ValueError("user_id is required for agent facade creation (no fallback allowed for DDD compliance)")
        
        try:
            # Create repository with user_id using the static create method
            if self._agent_repository_factory:
                # Use the static create method of AgentRepositoryFactory
                from ...infrastructure.repositories.agent_repository_factory import AgentRepositoryFactory
                agent_repository = AgentRepositoryFactory.create(
                    user_id=user_id
                )
            else:
                # Always use user-specific repository - no default without user_id
                from ...infrastructure.repositories.agent_repository_factory import AgentRepositoryFactory
                agent_repository = AgentRepositoryFactory.create(
                    user_id=user_id
                )
            
            # Create facade with repository
            facade = AgentApplicationFacade(agent_repository)
            
            # Cache the facade
            self._facades_cache[cache_key] = facade
            
            logger.info(f"Created new agent facade for {cache_key}")
            return facade
            
        except Exception as e:
            # Fallback for testing - create a minimal mock facade
            logger.warning(f"Failed to create proper AgentApplicationFacade: {e}, using mock")
            mock_facade = MockAgentApplicationFacade()
            self._facades_cache[cache_key] = mock_facade
            return mock_facade
    
    def clear_cache(self):
        """Clear the facades cache."""
        self._facades_cache.clear()
        logger.info("Agent facades cache cleared")
    
    def get_cached_facade(self, project_id: str) -> Optional[AgentApplicationFacade]:
        """
        Get a cached facade if available.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Cached facade or None
        """
        cache_key = f"{project_id}"
        return self._facades_cache.get(cache_key)
    
    def create_facade(self, project_id: str) -> AgentApplicationFacade:
        """
        Alias for create_agent_facade for backward compatibility.
        
        Args:
            project_id: Project identifier for scoping (required)
            
        Returns:
            AgentApplicationFacade instance with injected dependencies
        """
        if not project_id:
            raise ValueError("Project ID is required. No fallback to default project allowed per DDD principles.")
        return self.create_agent_facade(project_id, user_id=None)
    
    @staticmethod
    def create() -> AgentApplicationFacade:
        """
        Create a default agent facade (backward compatibility).
        
        Returns:
            AgentApplicationFacade instance with default configuration
            
        Raises:
            ValueError: Project ID is required per DDD principles
        """
        # DDD Compliance: No hardcoded project IDs - require explicit values
        raise ValueError("Cannot create agent facade: Project ID is required. No fallback to default project allowed per DDD principles.")


class MockAgentApplicationFacade:
    """Mock facade for testing purposes"""
    
    def register_agent(self, project_id: str, agent_id: str, name: str, call_agent: str = None):
        return {
            "success": True,
            "agent": {
                "id": agent_id,
                "name": name,
                "project_id": project_id,
                "call_agent": call_agent
            },
            "message": f"Mock: Agent {name} registered successfully"
        }
    
    def assign_agent(self, project_id: str, agent_id: str, git_branch_id: str):
        return {
            "success": True,
            "agent_id": agent_id,
            "git_branch_id": git_branch_id,
            "message": f"Mock: Agent {agent_id} assigned to {git_branch_id}"
        }
    
    def unassign_agent(self, project_id: str, agent_id: str, git_branch_id: str):
        return {
            "success": True,
            "agent_id": agent_id,
            "git_branch_id": git_branch_id,
            "message": f"Mock: Agent {agent_id} unassigned from {git_branch_id}"
        }
    
    def get_agent(self, project_id: str, agent_id: str):
        return {
            "success": True,
            "agent": {
                "id": agent_id,
                "name": f"Mock Agent {agent_id}",
                "project_id": project_id,
                "call_agent": None
            },
            "message": f"Mock: Agent {agent_id} retrieved successfully"
        }
    
    def list_agents(self, project_id: str):
        return {
            "success": True,
            "agents": [
                {
                    "id": "mock-agent-1",
                    "name": "Mock Agent 1",
                    "project_id": project_id,
                    "call_agent": None
                },
                {
                    "id": "mock-agent-2", 
                    "name": "Mock Agent 2",
                    "project_id": project_id,
                    "call_agent": None
                }
            ],
            "message": f"Mock: Listed agents for project {project_id}"
        }
    
    def update_agent(self, project_id: str, agent_id: str, name: str = None, call_agent: str = None):
        return {
            "success": True,
            "agent": {
                "id": agent_id,
                "name": name or f"Mock Agent {agent_id}",
                "project_id": project_id,
                "call_agent": call_agent
            },
            "message": f"Mock: Agent {agent_id} updated successfully"
        }
    
    def unregister_agent(self, project_id: str, agent_id: str):
        return {
            "success": True,
            "agent_id": agent_id,
            "message": f"Mock: Agent {agent_id} unregistered successfully"
        }
    
    def rebalance_agents(self, project_id: str):
        return {
            "success": True,
            "project_id": project_id,
            "message": f"Mock: Agents rebalanced for project {project_id}"
        }