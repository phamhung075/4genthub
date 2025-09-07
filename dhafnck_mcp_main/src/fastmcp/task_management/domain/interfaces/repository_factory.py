"""Repository Factory Interface - Domain Layer"""

from abc import ABC, abstractmethod
from typing import TypeVar, Type, Any


# Generic type for repositories
T = TypeVar('T')


class IRepository(ABC):
    """Base repository interface"""
    
    @abstractmethod
    async def find_by_id(self, id: Any) -> Any:
        """Find entity by ID"""
        pass
    
    @abstractmethod
    async def find_all(self) -> list:
        """Find all entities"""
        pass
    
    @abstractmethod
    async def save(self, entity: Any) -> Any:
        """Save entity"""
        pass
    
    @abstractmethod
    async def delete(self, entity: Any) -> bool:
        """Delete entity"""
        pass


class ITaskRepository(IRepository):
    """Task repository interface"""
    pass


class IProjectRepository(IRepository):
    """Project repository interface"""
    pass


class IGitBranchRepository(IRepository):
    """Git branch repository interface"""
    pass


class IAgentRepository(IRepository):
    """Agent repository interface"""
    pass


class IContextRepository(IRepository):
    """Context repository interface"""
    pass


class ISubtaskRepository(IRepository):
    """Subtask repository interface"""
    pass


class IRepositoryFactory(ABC):
    """Domain interface for repository factory"""
    
    @abstractmethod
    def create_task_repository(self) -> ITaskRepository:
        """Create task repository"""
        pass
    
    @abstractmethod
    def create_project_repository(self) -> IProjectRepository:
        """Create project repository"""
        pass
    
    @abstractmethod
    def create_git_branch_repository(self) -> IGitBranchRepository:
        """Create git branch repository"""
        pass
    
    @abstractmethod
    def create_agent_repository(self) -> IAgentRepository:
        """Create agent repository"""
        pass
    
    @abstractmethod
    def create_context_repository(self) -> IContextRepository:
        """Create context repository"""
        pass
    
    @abstractmethod
    def create_subtask_repository(self) -> ISubtaskRepository:
        """Create subtask repository"""
        pass


class ITaskRepositoryFactory(ABC):
    """Task-specific repository factory interface"""
    
    @abstractmethod
    def create_repository(self) -> ITaskRepository:
        """Create task repository"""
        pass


class IProjectRepositoryFactory(ABC):
    """Project-specific repository factory interface"""
    
    @abstractmethod
    def create_repository(self) -> IProjectRepository:
        """Create project repository"""
        pass


class IGitBranchRepositoryFactory(ABC):
    """Git branch-specific repository factory interface"""
    
    @abstractmethod
    def create_repository(self) -> IGitBranchRepository:
        """Create git branch repository"""
        pass