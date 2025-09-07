"""Facade Service for Application Layer

This service provides facade instances to the interface layer without exposing
the factory implementation details. This maintains proper DDD boundaries where
the interface layer doesn't know about how facades are constructed.

DDD Compliance:
- Application layer service that can be called by interface layer
- Encapsulates all factory logic within application layer
- Interface layer only knows about this service, not factories
- Proper contextual facade creation with user/project/branch isolation
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FacadeService:
    """
    Service that provides facades to the interface layer.
    
    This service acts as the single point of contact for the interface layer
    to obtain application facades. It encapsulates all factory logic and 
    contextual facade creation within the application layer.
    
    This follows DDD principles:
    - Interface layer calls this service
    - Service uses factories internally
    - Factories are hidden from interface layer
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get singleton instance of the facade service"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_task_facade(self, 
                       project_id: Optional[str] = None,
                       git_branch_id: Optional[str] = None,
                       user_id: Optional[str] = None):
        """
        Get a task facade with proper context.
        
        Args:
            project_id: Optional project identifier
            git_branch_id: Optional git branch identifier
            user_id: Optional user identifier
            
        Returns:
            TaskApplicationFacade configured for the given context
        """
        from ..factories.task_facade_factory import TaskFacadeFactory
        
        factory = TaskFacadeFactory.get_instance()
        return factory.create_task_facade(
            project_id=project_id,
            git_branch_id=git_branch_id,
            user_id=user_id
        )
    
    def get_subtask_facade(self,
                          project_id: Optional[str] = None,
                          git_branch_id: Optional[str] = None,
                          user_id: Optional[str] = None):
        """
        Get a subtask facade with proper context.
        
        Args:
            project_id: Optional project identifier
            git_branch_id: Optional git branch identifier
            user_id: Optional user identifier
            
        Returns:
            SubtaskApplicationFacade configured for the given context
        """
        from ..factories.subtask_facade_factory import SubtaskFacadeFactory
        
        factory = SubtaskFacadeFactory.get_instance()
        return factory.create_facade(
            project_id=project_id,
            git_branch_id=git_branch_id,
            user_id=user_id
        )
    
    def get_project_facade(self,
                          user_id: Optional[str] = None):
        """
        Get a project facade with proper context.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            ProjectApplicationFacade configured for the given context
        """
        from ..factories.project_facade_factory import ProjectFacadeFactory
        
        factory = ProjectFacadeFactory.get_instance()
        return factory.create_project_facade(user_id=user_id)
    
    def get_branch_facade(self,
                         project_id: Optional[str] = None,
                         user_id: Optional[str] = None):
        """
        Get a git branch facade with proper context.
        
        Args:
            project_id: Optional project identifier
            user_id: Optional user identifier
            
        Returns:
            GitBranchApplicationFacade configured for the given context
        """
        from ..factories.git_branch_facade_factory import GitBranchFacadeFactory
        
        factory = GitBranchFacadeFactory.get_instance()
        return factory.create_facade(
            project_id=project_id,
            user_id=user_id
        )
    
    def get_agent_facade(self,
                        project_id: Optional[str] = None,
                        user_id: Optional[str] = None):
        """
        Get an agent facade with proper context.
        
        Args:
            project_id: Optional project identifier
            user_id: Optional user identifier
            
        Returns:
            AgentApplicationFacade configured for the given context
        """
        from ..factories.agent_facade_factory import AgentFacadeFactory
        
        factory = AgentFacadeFactory()
        return factory.create_agent_facade(
            project_id=project_id,
            user_id=user_id
        )
    
    def get_context_facade(self,
                          user_id: Optional[str] = None,
                          project_id: Optional[str] = None,
                          git_branch_id: Optional[str] = None):
        """
        Get a unified context facade with proper context.
        
        Args:
            user_id: Optional user identifier
            project_id: Optional project identifier
            git_branch_id: Optional git branch identifier
            
        Returns:
            UnifiedContextFacade configured for the given context
        """
        from ..factories.unified_context_facade_factory import UnifiedContextFacadeFactory
        
        factory = UnifiedContextFacadeFactory.get_instance()
        return factory.create_facade(
            user_id=user_id,
            project_id=project_id,
            git_branch_id=git_branch_id
        )
    
    def get_token_facade(self,
                        user_id: Optional[str] = None):
        """
        Get a token facade with proper context.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            TokenApplicationFacade configured for the given context
        """
        from ..factories.token_facade_factory import TokenFacadeFactory
        
        factory = TokenFacadeFactory()
        return factory.create_token_facade()
    
    def get_auth_facade(self):
        """
        Get an auth facade.
        
        Returns:
            AuthApplicationFacade instance
        """
        from ..facades.auth_application_facade import AuthApplicationFacade
        
        # Auth facade doesn't need a factory
        return AuthApplicationFacade()
    
    @classmethod
    def get_unified_context_facade(cls,
                                  user_id: Optional[str] = None,
                                  project_id: Optional[str] = None,
                                  git_branch_id: Optional[str] = None):
        """
        Static method to get a unified context facade.
        
        This is a convenience method for services that need quick access
        to the unified context facade without creating a FacadeService instance.
        
        Args:
            user_id: Optional user identifier
            project_id: Optional project identifier
            git_branch_id: Optional git branch identifier
            
        Returns:
            UnifiedContextFacade configured for the given context
        """
        instance = cls.get_instance()
        return instance.get_context_facade(
            user_id=user_id,
            project_id=project_id,
            git_branch_id=git_branch_id
        )