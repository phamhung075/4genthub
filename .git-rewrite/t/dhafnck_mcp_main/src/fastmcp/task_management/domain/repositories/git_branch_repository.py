"""Git Branch Repository Interface

Domain layer repository interface for git branch operations.
Defines the contract for git branch persistence operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..entities.git_branch import GitBranch


class GitBranchRepository(ABC):
    """Repository interface for git branch operations"""
    
    @abstractmethod
    async def create_git_branch(self, project_id: str, git_branch_name: str, git_branch_description: str = "") -> Dict[str, Any]:
        """Create a new git branch"""
        pass
    
    @abstractmethod
    async def get_git_branch_by_id(self, git_branch_id: str) -> Dict[str, Any]:
        """Get git branch by ID"""
        pass
    
    @abstractmethod
    async def get_git_branch_by_name(self, project_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Get git branch by name within a project"""
        pass
    
    @abstractmethod
    async def list_git_branchs(self, project_id: str) -> Dict[str, Any]:
        """List all git branches for a project"""
        pass
    
    @abstractmethod
    async def update_git_branch(self, git_branch_id: str, git_branch_name: Optional[str] = None, git_branch_description: Optional[str] = None) -> Dict[str, Any]:
        """Update git branch information"""
        pass
    
    @abstractmethod
    async def delete_git_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Delete a git branch"""
        pass
    
    @abstractmethod
    async def assign_agent_to_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Assign an agent to a git branch"""
        pass
    
    @abstractmethod
    async def unassign_agent_from_branch(self, project_id: str, agent_id: str, git_branch_name: str) -> Dict[str, Any]:
        """Unassign an agent from a git branch"""
        pass
    
    @abstractmethod
    async def get_branch_statistics(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Get statistics for a git branch"""
        pass
    
    @abstractmethod
    async def archive_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Archive a git branch"""
        pass
    
    @abstractmethod
    async def restore_branch(self, project_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Restore an archived git branch"""
        pass