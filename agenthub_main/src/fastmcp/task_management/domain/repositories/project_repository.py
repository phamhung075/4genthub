"""Project Repository Interface"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..entities.project import Project


class ProjectRepository(ABC):
    """Abstract repository for project persistence operations"""
    
    @abstractmethod
    async def save(self, project: Project) -> None:
        """Save a project to the repository"""
        pass
    
    @abstractmethod
    async def find_by_id(self, project_id: str) -> Optional[Project]:
        """Find a project by its ID"""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Project]:
        """Find all projects"""
        pass
    
    @abstractmethod
    async def delete(self, project_id: str) -> bool:
        """Delete a project by its ID"""
        pass
    
    @abstractmethod
    async def exists(self, project_id: str) -> bool:
        """Check if a project exists"""
        pass
    
    @abstractmethod
    async def update(self, project: Project) -> None:
        """Update an existing project"""
        pass
    
    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Project]:
        """Find a project by its name"""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Count total number of projects"""
        pass
    
    @abstractmethod
    async def find_projects_with_agent(self, agent_id: str) -> List[Project]:
        """Find projects that have a specific agent registered"""
        pass
    
    @abstractmethod
    async def find_projects_by_status(self, status: str) -> List[Project]:
        """Find projects by their status"""
        pass
    
    @abstractmethod
    async def get_project_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all projects"""
        pass

    @abstractmethod
    async def unassign_agent_from_tree(self, project_id: str, agent_id: str, git_branch_id: str) -> Dict[str, Any]:
        """Unassign an agent from a specific task tree within a project."""
        pass