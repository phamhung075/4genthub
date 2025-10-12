"""Central Repository Factory with Environment-Based Switching

This factory properly checks environment variables to determine which repository implementation to use.
It supports SQLite for tests, Supabase for production, and Redis caching when enabled.
"""

import os
import logging
from typing import Optional, Any
from .utils import get_repository_config

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """Central factory that checks environment variables for repository selection"""
    
    @staticmethod
    def get_environment_config():
        """Get environment configuration for repository selection"""
        return get_repository_config()
    
    @staticmethod
    def get_task_repository(project_id: Optional[str] = None, 
                           git_branch_name: Optional[str] = None,
                           user_id: Optional[str] = None):
        """Get task repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating task repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockTaskRepository
            logger.info("[RepositoryFactory] Using MockTaskRepository for test environment")
            return MockTaskRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses ORM repository directly
            from .orm.task_repository import ORMTaskRepository
            base_repository = ORMTaskRepository(
                session=None,
                git_branch_id=None,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
            logger.info("[RepositoryFactory] SQLite configured, using ORMTaskRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses ORM repository directly
            from .orm.task_repository import ORMTaskRepository
            base_repository = ORMTaskRepository(
                session=None,
                git_branch_id=None,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
            logger.info("[RepositoryFactory] Supabase configured, using ORMTaskRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses ORM repository directly
            from .orm.task_repository import ORMTaskRepository
            base_repository = ORMTaskRepository(
                session=None,
                git_branch_id=None,
                project_id=project_id,
                git_branch_name=git_branch_name,
                user_id=user_id
            )
            logger.info("[RepositoryFactory] PostgreSQL configured, using ORMTaskRepository")

        # NO FALLBACK - If we can't create the correct repository, FAIL
        if not base_repository:
            error_msg = (
                f"❌ CRITICAL: Failed to create repository for database type: {config['database_type']}\n"
                "NO FALLBACK ALLOWED - Server must use the configured database type!\n"
                "Check your DATABASE_TYPE setting and ensure the database is accessible."
            )
            logger.error(error_msg)

            # Exit immediately - no fallback repositories
            import sys
            sys.exit(1)
        
        # Wrap with cache if enabled and not in test environment
        # TEMPORARILY DISABLED: CachedTaskRepository has async methods but NextTaskUseCase expects sync
        # This causes "coroutine object is not iterable" errors
        # TODO: Fix by either making CachedTaskRepository sync or updating use cases to handle async
        if False and config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
            try:
                from .cached.cached_task_repository import CachedTaskRepository
                logger.info("[RepositoryFactory] Wrapping with CachedTaskRepository")
                return CachedTaskRepository(base_repository)
            except ImportError:
                logger.warning("CachedTaskRepository not available, using base repository")
        
        return base_repository
    
    @staticmethod
    def get_project_repository():
        """Get project repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating project repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockProjectRepository
            logger.info("[RepositoryFactory] Using MockProjectRepository for test environment")
            return MockProjectRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses ORM repository directly
            from .orm.project_repository import ORMProjectRepository
            base_repository = ORMProjectRepository()
            logger.info("[RepositoryFactory] SQLite configured, using ORMProjectRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses ORM repository directly
            from .orm.project_repository import ORMProjectRepository
            base_repository = ORMProjectRepository()
            logger.info("[RepositoryFactory] Supabase configured, using ORMProjectRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses ORM repository directly - no separate implementation needed
            logger.info("[RepositoryFactory] PostgreSQL configured, using ORMProjectRepository")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.project_repository import ORMProjectRepository
            base_repository = ORMProjectRepository()
            logger.info("[RepositoryFactory] Using ORMProjectRepository (fallback)")
        
        # Wrap with cache if enabled and not in test environment
        if config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
            try:
                from .cached.cached_project_repository import CachedProjectRepository
                logger.info("[RepositoryFactory] Wrapping with CachedProjectRepository")
                return CachedProjectRepository(base_repository)
            except ImportError:
                logger.warning("CachedProjectRepository not available, using base repository")
        
        return base_repository
    
    @staticmethod
    def get_git_branch_repository(user_id: Optional[str] = None):
        """Get git branch repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()

        logger.debug(f"[RepositoryFactory] Creating git branch repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockGitBranchRepository
            logger.info("[RepositoryFactory] Using MockGitBranchRepository for test environment")
            return MockGitBranchRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses ORM repository directly
            from .orm.git_branch_repository import ORMGitBranchRepository
            base_repository = ORMGitBranchRepository(user_id=user_id)
            logger.info("[RepositoryFactory] SQLite configured, using ORMGitBranchRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses ORM repository directly
            from .orm.git_branch_repository import ORMGitBranchRepository
            base_repository = ORMGitBranchRepository(user_id=user_id)
            logger.info("[RepositoryFactory] Supabase configured, using ORMGitBranchRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses ORM repository directly - no separate implementation needed
            from .orm.git_branch_repository import ORMGitBranchRepository
            base_repository = ORMGitBranchRepository(user_id=user_id)
            logger.info("[RepositoryFactory] PostgreSQL configured, using ORMGitBranchRepository")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.git_branch_repository import ORMGitBranchRepository
            base_repository = ORMGitBranchRepository(user_id=user_id)
            logger.info("[RepositoryFactory] Using ORMGitBranchRepository (fallback)")
        
        # Wrap with cache if enabled and not in test environment
        if config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
            try:
                from .cached.cached_git_branch_repository import CachedGitBranchRepository
                logger.info("[RepositoryFactory] Wrapping with CachedGitBranchRepository")
                return CachedGitBranchRepository(base_repository)
            except ImportError:
                logger.warning("CachedGitBranchRepository not available, using base repository")
        
        return base_repository
    
    @staticmethod
    def get_subtask_repository(user_id: Optional[str] = None):
        """Get subtask repository based on environment configuration
        
        Args:
            user_id: Optional user ID for repository scoping
            
        Returns:
            SubtaskRepository instance
        """
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating subtask repository with config: {config}, user_id: {user_id}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockSubtaskRepository
            logger.info("[RepositoryFactory] Using MockSubtaskRepository for test environment")
            return MockSubtaskRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses ORM repository directly
            from .orm.subtask_repository import ORMSubtaskRepository
            base_repository = ORMSubtaskRepository(user_id=user_id)
            logger.info("[RepositoryFactory] SQLite configured, using ORMSubtaskRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses ORM repository directly
            from .orm.subtask_repository import ORMSubtaskRepository
            base_repository = ORMSubtaskRepository(user_id=user_id)
            logger.info("[RepositoryFactory] Supabase configured, using ORMSubtaskRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses ORM repository directly - no separate implementation needed
            logger.info("[RepositoryFactory] PostgreSQL configured, using ORMSubtaskRepository")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.subtask_repository import ORMSubtaskRepository
            base_repository = ORMSubtaskRepository(user_id=user_id)
            logger.info(f"[RepositoryFactory] Using ORMSubtaskRepository (fallback) with user_id: {user_id}")
        
        # Wrap with cache if enabled and not in test environment
        if config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
            try:
                from .cached.cached_subtask_repository import CachedSubtaskRepository
                logger.info("[RepositoryFactory] Wrapping with CachedSubtaskRepository")
                return CachedSubtaskRepository(base_repository)
            except ImportError:
                logger.warning("CachedSubtaskRepository not available, using base repository")
        
        return base_repository
    
    @staticmethod
    def get_agent_repository():
        """Get agent repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating agent repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockAgentRepository
            logger.info("[RepositoryFactory] Using MockAgentRepository for test environment")
            return MockAgentRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses ORM repository directly
            from .orm.agent_repository import ORMAgentRepository
            base_repository = ORMAgentRepository()
            logger.info("[RepositoryFactory] SQLite configured, using ORMAgentRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses ORM repository directly
            from .orm.agent_repository import ORMAgentRepository
            base_repository = ORMAgentRepository()
            logger.info("[RepositoryFactory] Supabase configured, using ORMAgentRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses ORM repository directly - no separate implementation needed
            logger.info("[RepositoryFactory] PostgreSQL configured, using ORMAgentRepository")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.agent_repository import ORMAgentRepository
            base_repository = ORMAgentRepository()
            logger.info("[RepositoryFactory] Using ORMAgentRepository (fallback)")
        
        # Wrap with cache if enabled and not in test environment
        if config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
            try:
                from .cached.cached_agent_repository import CachedAgentRepository
                logger.info("[RepositoryFactory] Wrapping with CachedAgentRepository")
                return CachedAgentRepository(base_repository)
            except ImportError:
                logger.warning("CachedAgentRepository not available, using base repository")
        
        return base_repository
    
    @staticmethod
    def get_context_repository():
        """Get context repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating context repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            try:
                from .mock_repository_factory import MockContextRepository
                logger.info("[RepositoryFactory] Using MockContextRepository for test environment")
                return MockContextRepository()
            except ImportError:
                logger.warning("MockContextRepository not available, using mock task context")
                from .mock_task_context_repository import MockTaskContextRepository
                return MockTaskContextRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            # SQLite uses TaskContextRepository directly
            from .task_context_repository import TaskContextRepository
            from ..database.database_config import get_db_config
            db_config = get_db_config()
            base_repository = TaskContextRepository(db_config.SessionLocal)
            logger.info("[RepositoryFactory] SQLite configured, using TaskContextRepository")
        
        elif config['database_type'] == 'supabase':
            # Supabase uses TaskContextRepository directly
            from .task_context_repository import TaskContextRepository
            from ..database.database_config import get_db_config
            db_config = get_db_config()
            base_repository = TaskContextRepository(db_config.SessionLocal)
            logger.info("[RepositoryFactory] Supabase configured, using TaskContextRepository")
        
        elif config['database_type'] == 'postgresql':
            # PostgreSQL uses TaskContextRepository directly - no separate implementation needed
            logger.info("[RepositoryFactory] PostgreSQL configured, using TaskContextRepository")
        
        # Fallback to TaskContextRepository (context is part of task system)
        if not base_repository:
            from .task_context_repository import TaskContextRepository
            from ..database.database_config import get_db_config
            
            db_config = get_db_config()
            base_repository = TaskContextRepository(db_config.SessionLocal)
            logger.info("[RepositoryFactory] Using TaskContextRepository (fallback)")
        
        return base_repository