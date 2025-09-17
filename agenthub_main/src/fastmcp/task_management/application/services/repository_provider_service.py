"""Repository Provider Service for Application Layer

This service provides repository instances to the application layer without exposing
infrastructure details. It acts as a boundary between application and infrastructure
layers, maintaining proper DDD separation.

DDD Compliance:
- Application layer service that can be used by facades and other application services
- Encapsulates all repository creation logic
- Infrastructure details are hidden from application layer
- Provides typed repository interfaces, not concrete implementations
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ...domain.repositories.task_repository import TaskRepository
from ...domain.repositories.subtask_repository import SubtaskRepository
from ...domain.repositories.project_repository import ProjectRepository
from ...domain.repositories.agent_repository import AgentRepository
from ...domain.repositories.context_repository import ContextRepository
from ...domain.repositories.git_branch_repository import GitBranchRepository
from ...domain.repositories.token_repository_interface import ITokenRepository

logger = logging.getLogger(__name__)


class RepositoryProviderService:
    """
    Provides repository instances to the application layer.
    
    This service is responsible for creating and managing repository instances
    while keeping infrastructure details hidden from the application layer.
    All methods return repository interfaces, not concrete implementations.
    """
    
    _instance = None
    _repositories: Dict[str, Any] = {}
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of the repository provider service"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_task_repository(self, project_id: Optional[str] = None, git_branch_name: Optional[str] = None, 
                           user_id: Optional[str] = None, session: Optional[Session] = None) -> TaskRepository:
        """
        Get a task repository instance.
        
        Args:
            project_id: Optional project identifier (will try to auto-resolve if None)
            git_branch_name: Optional branch name (defaults to "main")
            user_id: Optional user identifier
            session: Optional database session
            
        Returns:
            TaskRepositoryInterface implementation
        """
        # Import only when needed (lazy loading)
        from ...infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        
        # For DDD compliance, if project_id is not provided, return a generic repository
        # that can work across projects (for GET operations without project context)
        if project_id is None:
            # Use ORM repository which doesn't require project_id upfront
            from ...infrastructure.repositories.orm.task_repository import ORMTaskRepository
            return ORMTaskRepository(
                session=session,
                git_branch_id=None,
                project_id=None,
                git_branch_name=git_branch_name or "main",
                user_id=user_id
            )
        
        # If project_id is provided, use the factory's create_repository method
        factory = TaskRepositoryFactory()
        return factory.create_repository(project_id, git_branch_name or "main", user_id)
    
    def get_subtask_repository(self, project_id: Optional[str] = None, git_branch_name: Optional[str] = None,
                              user_id: Optional[str] = None, session: Optional[Session] = None) -> SubtaskRepository:
        """
        Get a subtask repository instance.
        
        Args:
            project_id: Optional project identifier
            git_branch_name: Optional branch name (defaults to "main")
            user_id: Optional user identifier
            session: Optional database session
            
        Returns:
            SubtaskRepositoryInterface implementation
        """
        from ...infrastructure.repositories.subtask_repository_factory import SubtaskRepositoryFactory
        
        factory = SubtaskRepositoryFactory()
        
        # For DDD compliance, if project_id is not provided, use ORM repository
        if project_id is None:
            # Use ORM repository which only needs user_id
            return factory.create_orm_subtask_repository(user_id=user_id)
        
        # If project_id is provided, use the standard create method
        return factory.create_subtask_repository(project_id, git_branch_name or "main", user_id)
    
    def get_project_repository(self, user_id: Optional[str] = None, session: Optional[Session] = None) -> ProjectRepository:
        """
        Get a project repository instance.
        
        Args:
            user_id: User identifier (required for authentication)
            session: Optional database session
            
        Returns:
            ProjectRepositoryInterface implementation
        """
        # ProjectRepositoryFactory uses static methods, not instance methods
        from ...infrastructure.repositories.project_repository_factory import ProjectRepositoryFactory
        
        # Use the create method which is a classmethod
        return ProjectRepositoryFactory.create(user_id=user_id)
    
    def get_agent_repository(self, session: Optional[Session] = None) -> AgentRepository:
        """
        Get an agent repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            AgentRepositoryInterface implementation
        """
        if 'agent' not in self._repositories:
            from ...infrastructure.repositories.agent_repository_factory import AgentRepositoryFactory
            factory = AgentRepositoryFactory()
            self._repositories['agent'] = factory
        
        return self._repositories['agent'].create_repository(session)
    
    def get_git_branch_repository(self, session: Optional[Session] = None, user_id: Optional[str] = None) -> GitBranchRepository:
        """
        Get a git branch repository instance.
        
        Args:
            session: Optional database session
            user_id: Optional user identifier
            
        Returns:
            GitBranchRepositoryInterface implementation
        """
        # GitBranchRepositoryFactory uses static methods, not instance methods
        from ...infrastructure.repositories.git_branch_repository_factory import GitBranchRepositoryFactory
        
        # Use the create method which is a classmethod
        return GitBranchRepositoryFactory.create(user_id=user_id)
    
    def get_global_context_repository(self, session: Optional[Session] = None) -> ContextRepository:
        """
        Get a global context repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            GlobalContextRepositoryInterface implementation
        """
        if 'global_context' not in self._repositories:
            from ...infrastructure.repositories.global_context_repository import GlobalContextRepository
            self._repositories['global_context'] = GlobalContextRepository(session)
        
        return self._repositories['global_context']
    
    def get_project_context_repository(self, session: Optional[Session] = None) -> ContextRepository:
        """
        Get a project context repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            ProjectContextRepositoryInterface implementation
        """
        if 'project_context' not in self._repositories:
            from ...infrastructure.repositories.project_context_repository import ProjectContextRepository
            self._repositories['project_context'] = ProjectContextRepository(session)
        
        return self._repositories['project_context']
    
    def get_branch_context_repository(self, session: Optional[Session] = None) -> ContextRepository:
        """
        Get a branch context repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            BranchContextRepositoryInterface implementation
        """
        if 'branch_context' not in self._repositories:
            from ...infrastructure.repositories.branch_context_repository import BranchContextRepository
            self._repositories['branch_context'] = BranchContextRepository(session)
        
        return self._repositories['branch_context']
    
    def get_task_context_repository(self, session: Optional[Session] = None) -> ContextRepository:
        """
        Get a task context repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            TaskContextRepositoryInterface implementation
        """
        if 'task_context' not in self._repositories:
            from ...infrastructure.repositories.task_context_repository import TaskContextRepository
            self._repositories['task_context'] = TaskContextRepository(session)
        
        return self._repositories['task_context']
    
    def get_token_repository(self, session: Optional[Session] = None) -> ITokenRepository:
        """
        Get a token repository instance.
        
        Args:
            session: Optional database session
            
        Returns:
            TokenRepositoryInterface implementation
        """
        if 'token' not in self._repositories:
            from ...infrastructure.repositories.token_repository import TokenRepository
            self._repositories['token'] = TokenRepository(session)
        
        return self._repositories['token']
    
    def clear_cache(self):
        """Clear all cached repository instances"""
        self._repositories.clear()
        logger.info("Repository cache cleared")