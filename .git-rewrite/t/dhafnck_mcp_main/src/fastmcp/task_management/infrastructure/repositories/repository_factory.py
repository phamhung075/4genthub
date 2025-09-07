"""Central Repository Factory with Environment-Based Switching

This factory properly checks environment variables to determine which repository implementation to use.
It supports SQLite for tests, Supabase for production, and Redis caching when enabled.
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class RepositoryFactory:
    """Central factory that checks environment variables for repository selection"""
    
    @staticmethod
    def get_environment_config():
        """Get environment configuration for repository selection"""
        return {
            'environment': os.getenv('ENVIRONMENT', 'production'),
            'database_type': os.getenv('DATABASE_TYPE', 'supabase'),
            'redis_enabled': os.getenv('REDIS_ENABLED', 'true').lower() == 'true',
            'use_cache': os.getenv('USE_CACHE', 'true').lower() == 'true'
        }
    
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
            try:
                from .sqlite.sqlite_task_repository import SQLiteTaskRepository
                base_repository = SQLiteTaskRepository(project_id, git_branch_name, user_id)
                logger.info("[RepositoryFactory] Using SQLiteTaskRepository")
            except ImportError:
                logger.warning("SQLiteTaskRepository not available, falling back to ORM")
        
        elif config['database_type'] == 'supabase':
            try:
                from .supabase.supabase_task_repository import SupabaseTaskRepository
                base_repository = SupabaseTaskRepository(project_id, git_branch_name, user_id)
                logger.info("[RepositoryFactory] Using SupabaseTaskRepository")
            except ImportError:
                logger.warning("SupabaseTaskRepository not available, falling back to ORM")
        
        elif config['database_type'] == 'postgresql':
            try:
                from .postgresql.postgresql_task_repository import PostgreSQLTaskRepository
                base_repository = PostgreSQLTaskRepository(project_id, git_branch_name, user_id)
                logger.info("[RepositoryFactory] Using PostgreSQLTaskRepository")
            except ImportError:
                logger.warning("PostgreSQLTaskRepository not available, falling back to ORM")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.task_repository import ORMTaskRepository
            base_repository = ORMTaskRepository(project_id, git_branch_name, user_id)
            logger.info("[RepositoryFactory] Using ORMTaskRepository (fallback)")
        
        # Wrap with cache if enabled and not in test environment
        if config['redis_enabled'] and config['use_cache'] and config['environment'] != 'test':
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
            try:
                from .sqlite.sqlite_project_repository import SQLiteProjectRepository
                base_repository = SQLiteProjectRepository()
                logger.info("[RepositoryFactory] Using SQLiteProjectRepository")
            except ImportError:
                logger.warning("SQLiteProjectRepository not available, falling back to ORM")
        
        elif config['database_type'] == 'supabase':
            try:
                from .supabase.supabase_project_repository import SupabaseProjectRepository
                base_repository = SupabaseProjectRepository()
                logger.info("[RepositoryFactory] Using SupabaseProjectRepository")
            except ImportError:
                logger.warning("SupabaseProjectRepository not available, falling back to ORM")
        
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
    def get_git_branch_repository():
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
            try:
                from .sqlite.sqlite_git_branch_repository import SQLiteGitBranchRepository
                base_repository = SQLiteGitBranchRepository()
                logger.info("[RepositoryFactory] Using SQLiteGitBranchRepository")
            except ImportError:
                logger.warning("SQLiteGitBranchRepository not available, falling back to ORM")
        
        elif config['database_type'] == 'supabase':
            try:
                from .supabase.supabase_git_branch_repository import SupabaseGitBranchRepository
                base_repository = SupabaseGitBranchRepository()
                logger.info("[RepositoryFactory] Using SupabaseGitBranchRepository")
            except ImportError:
                logger.warning("SupabaseGitBranchRepository not available, falling back to ORM")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.git_branch_repository import ORMGitBranchRepository
            base_repository = ORMGitBranchRepository()
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
    def get_subtask_repository():
        """Get subtask repository based on environment configuration"""
        config = RepositoryFactory.get_environment_config()
        
        logger.debug(f"[RepositoryFactory] Creating subtask repository with config: {config}")
        
        # Test environment - use mock repository
        if config['environment'] == 'test':
            from .mock_repository_factory import MockSubtaskRepository
            logger.info("[RepositoryFactory] Using MockSubtaskRepository for test environment")
            return MockSubtaskRepository()
        
        # Determine base repository based on database type
        base_repository = None
        
        if config['database_type'] == 'sqlite':
            try:
                from .sqlite.sqlite_subtask_repository import SQLiteSubtaskRepository
                base_repository = SQLiteSubtaskRepository()
                logger.info("[RepositoryFactory] Using SQLiteSubtaskRepository")
            except ImportError:
                logger.warning("SQLiteSubtaskRepository not available, falling back to ORM")
        
        elif config['database_type'] == 'supabase':
            try:
                from .supabase.supabase_subtask_repository import SupabaseSubtaskRepository
                base_repository = SupabaseSubtaskRepository()
                logger.info("[RepositoryFactory] Using SupabaseSubtaskRepository")
            except ImportError:
                logger.warning("SupabaseSubtaskRepository not available, falling back to ORM")
        
        # Fallback to ORM repository
        if not base_repository:
            from .orm.subtask_repository import ORMSubtaskRepository
            base_repository = ORMSubtaskRepository()
            logger.info("[RepositoryFactory] Using ORMSubtaskRepository (fallback)")
        
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
        
        # For now, always use ORM repository for agents
        from .orm.agent_repository import ORMAgentRepository
        base_repository = ORMAgentRepository()
        logger.info("[RepositoryFactory] Using ORMAgentRepository")
        
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
        
        # For production, use task context repository (context is part of task system)
        from .task_context_repository import TaskContextRepository
        from ..database.database_config import get_db_config
        
        db_config = get_db_config()
        base_repository = TaskContextRepository(db_config.SessionLocal)
        logger.info("[RepositoryFactory] Using TaskContextRepository")
        
        return base_repository