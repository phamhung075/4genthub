"""Facade Provider for Interface Layer

This module provides a centralized way for the interface layer to access application facades
without directly importing factories from the application layer. This enforces proper DDD
boundaries where the interface layer only knows about facades, not their construction.

DDD Compliance:
- Interface layer imports this provider (same layer)
- Provider internally manages facade creation
- No direct factory imports in controllers
- Single point of facade access for all controllers
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FacadeProvider:
    """
    Provides access to application facades for the interface layer.
    
    This class acts as a boundary between the interface and application layers,
    ensuring that controllers don't directly import or know about factories.
    All facade creation is encapsulated here.
    """
    
    # Cached facade instances (singletons)
    _task_facade = None
    _subtask_facade = None
    _project_facade = None
    _branch_facade = None
    _agent_facade = None
    _context_facade = None
    _token_facade = None
    _auth_facade = None
    
    @classmethod
    def get_task_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the task application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            TaskApplicationFacade instance
        """
        if cls._task_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._task_facade = facade_service.get_task_facade(user_id=user_id)
            
        return cls._task_facade
    
    @classmethod
    def get_subtask_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the subtask application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            SubtaskApplicationFacade instance
        """
        if cls._subtask_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._subtask_facade = facade_service.get_subtask_facade(user_id=user_id,
                subtask_repository_factory=subtask_repo_factory,
                task_repository_factory=task_repo_factory,
                context_service=context_facade
            )
            
        return cls._subtask_facade
    
    @classmethod
    def get_project_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the project application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            ProjectApplicationFacade instance
        """
        if cls._project_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._project_facade = ProjectApplicationFacade(
                project_repository_factory=project_repo_factory,
                branch_repository_factory=branch_repo_factory,
                task_repository_factory=task_repo_factory,
                context_service=context_facade
            )
            
        return cls._project_facade
    
    @classmethod
    def get_branch_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the git branch application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            GitBranchApplicationFacade instance
        """
        if cls._branch_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._branch_facade = facade_service.get_branch_facade(user_id=user_id)
            
        return cls._branch_facade
    
    @classmethod
    def get_agent_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the agent application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            AgentApplicationFacade instance
        """
        if cls._agent_facade is None:
            from ..application.facades.agent_application_facade import AgentApplicationFacade
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._agent_facade = facade_service.get_agent_facade(user_id=user_id)
            
        return cls._agent_facade
    
    @classmethod
    def get_context_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the unified context application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            UnifiedContextFacade instance
        """
        if cls._context_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._context_facade = facade_service.get_context_facade(user_id=user_id)
            
        return cls._context_facade
    
    @classmethod
    def get_token_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the token application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            TokenApplicationFacade instance
        """
        if cls._token_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._token_facade = facade_service.get_token_facade(user_id=user_id)
            
        return cls._token_facade
    
    @classmethod
    def get_auth_facade(cls, session: Optional[Session] = None, user_id: Optional[str] = None):
        """
        Get the auth application facade.
        
        Args:
            session: Optional database session
            user_id: Optional user ID for context
            
        Returns:
            AuthApplicationFacade instance
        """
        if cls._auth_facade is None:
            # Use FacadeService from application layer - DDD compliant
            from ..application.services.facade_service import FacadeService
            
            # Get facade through the application layer service
            facade_service = FacadeService.get_instance()
            cls._auth_facade = facade_service.get_auth_facade()
            
        return cls._auth_facade
    
    @classmethod
    def clear_cache(cls):
        """
        Clear all cached facade instances.
        
        This should be called when you need to force recreation of facades,
        such as during testing or after configuration changes.
        """
        cls._task_facade = None
        cls._subtask_facade = None
        cls._project_facade = None
        cls._branch_facade = None
        cls._agent_facade = None
        cls._context_facade = None
        cls._token_facade = None
        cls._auth_facade = None
        logger.info("Facade cache cleared")