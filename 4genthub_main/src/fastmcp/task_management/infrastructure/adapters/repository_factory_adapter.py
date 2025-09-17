"""Repository Factory Adapter - Infrastructure Layer"""

from ...domain.interfaces.repository_factory import (
    IRepositoryFactory, ITaskRepository, IProjectRepository, IGitBranchRepository,
    IAgentRepository, IContextRepository, ISubtaskRepository,
    ITaskRepositoryFactory, IProjectRepositoryFactory, IGitBranchRepositoryFactory
)
from ..repositories.repository_factory import RepositoryFactory
from ..repositories.task_repository_factory import TaskRepositoryFactory
from ..repositories.project_repository_factory import ProjectRepositoryFactory
from ..repositories.git_branch_repository_factory import GitBranchRepositoryFactory


class TaskRepositoryAdapter(ITaskRepository):
    """Adapter for infrastructure task repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    async def find_by_id(self, id):
        """Find entity by ID"""
        return await self._repository.find_by_id(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class ProjectRepositoryAdapter(IProjectRepository):
    """Adapter for infrastructure project repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    async def find_by_id(self, id):
        """Find entity by ID"""
        return await self._repository.find_by_id(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class GitBranchRepositoryAdapter(IGitBranchRepository):
    """Adapter for infrastructure git branch repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    def get(self, id):
        """Get entity by ID - synchronous method"""
        if hasattr(self._repository, 'get'):
            return self._repository.get(id)
        elif hasattr(self._repository, 'find_by_id'):
            # Handle async repository - convert to sync
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._repository.find_by_id(id))
        return None
    
    def find_by_id(self, id):
        """Find entity by ID - synchronous method"""
        return self.get(id)
    
    async def find_by_id_async(self, id):
        """Find entity by ID - async method"""
        if hasattr(self._repository, 'find_by_id'):
            return await self._repository.find_by_id(id)
        return self.get(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class AgentRepositoryAdapter(IAgentRepository):
    """Adapter for infrastructure agent repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    async def find_by_id(self, id):
        """Find entity by ID"""
        return await self._repository.find_by_id(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class ContextRepositoryAdapter(IContextRepository):
    """Adapter for infrastructure context repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    async def find_by_id(self, id):
        """Find entity by ID"""
        return await self._repository.find_by_id(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class SubtaskRepositoryAdapter(ISubtaskRepository):
    """Adapter for infrastructure subtask repository"""
    
    def __init__(self, repository):
        self._repository = repository
    
    async def find_by_id(self, id):
        """Find entity by ID"""
        return await self._repository.find_by_id(id)
    
    async def find_all(self):
        """Find all entities"""
        return await self._repository.find_all()
    
    async def save(self, entity):
        """Save entity"""
        return await self._repository.save(entity)
    
    async def delete(self, entity):
        """Delete entity"""
        return await self._repository.delete(entity)


class RepositoryFactoryAdapter(IRepositoryFactory):
    """Adapter for infrastructure repository factory"""
    
    def __init__(self):
        self._factory = RepositoryFactory()
    
    def create_task_repository(self) -> ITaskRepository:
        """Create task repository"""
        repo = self._factory.create_task_repository()
        return TaskRepositoryAdapter(repo)
    
    def create_project_repository(self) -> IProjectRepository:
        """Create project repository"""
        repo = self._factory.create_project_repository()
        return ProjectRepositoryAdapter(repo)
    
    def create_git_branch_repository(self) -> IGitBranchRepository:
        """Create git branch repository"""
        repo = self._factory.create_git_branch_repository()
        return GitBranchRepositoryAdapter(repo)
    
    def create_agent_repository(self) -> IAgentRepository:
        """Create agent repository"""
        repo = self._factory.create_agent_repository()
        return AgentRepositoryAdapter(repo)
    
    def create_context_repository(self) -> IContextRepository:
        """Create context repository"""
        repo = self._factory.create_context_repository()
        return ContextRepositoryAdapter(repo)
    
    def create_subtask_repository(self) -> ISubtaskRepository:
        """Create subtask repository"""
        repo = self._factory.create_subtask_repository()
        return SubtaskRepositoryAdapter(repo)


class TaskRepositoryFactoryAdapter(ITaskRepositoryFactory):
    """Adapter for infrastructure task repository factory"""
    
    def __init__(self):
        self._factory = TaskRepositoryFactory()
    
    def create_repository(self) -> ITaskRepository:
        """Create task repository"""
        repo = self._factory.create_repository()
        return TaskRepositoryAdapter(repo)


class ProjectRepositoryFactoryAdapter(IProjectRepositoryFactory):
    """Adapter for infrastructure project repository factory"""
    
    def __init__(self):
        self._factory = ProjectRepositoryFactory()
    
    def create_repository(self) -> IProjectRepository:
        """Create project repository"""
        repo = self._factory.create_repository()
        return ProjectRepositoryAdapter(repo)


class GitBranchRepositoryFactoryAdapter(IGitBranchRepositoryFactory):
    """Adapter for infrastructure git branch repository factory"""
    
    def __init__(self):
        self._factory = GitBranchRepositoryFactory()
    
    def create_repository(self) -> IGitBranchRepository:
        """Create git branch repository"""
        repo = self._factory.create()  # Fixed: Use create() instead of create_repository()
        return GitBranchRepositoryAdapter(repo)
    
    def create(self) -> IGitBranchRepository:
        """Create git branch repository - alternate method name"""
        return self.create_repository()