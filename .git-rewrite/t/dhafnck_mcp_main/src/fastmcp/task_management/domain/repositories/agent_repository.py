"""Agent Repository Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class AgentRepository(ABC):
    """
    Domain repository interface for agent operations.
    Defines the contract for agent persistence and retrieval.
    """
    
    @abstractmethod
    def register_agent(self, project_id: str, agent_id: str, name: str, call_agent: str = None) -> Dict[str, Any]:
        """Register a new agent to a project"""
        pass
    
    @abstractmethod
    def unregister_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Unregister an agent from a project"""
        pass
    
    @abstractmethod
    def assign_agent_to_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Assign an agent to a task tree"""
        pass
    
    @abstractmethod
    def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str = None) -> Dict[str, Any]:
        """Unassign an agent from task tree(s)"""
        pass
    
    @abstractmethod
    def get_agent(self, project_id: str, agent_id: str) -> Dict[str, Any]:
        """Get agent details"""
        pass
    
    @abstractmethod
    def list_agents(self, project_id: str) -> Dict[str, Any]:
        """List all agents in a project"""
        pass
    
    @abstractmethod
    def update_agent(self, project_id: str, agent_id: str, name: str = None, call_agent: str = None) -> Dict[str, Any]:
        """Update agent details"""
        pass
    
    @abstractmethod
    def rebalance_agents(self, project_id: str) -> Dict[str, Any]:
        """Rebalance agent assignments across task trees"""
        pass