"""Test suite for RepositoryFactory class.

Tests the factory's ability to create appropriate repository instances based on
environment configuration for different environments (test, sqlite, supabase, postgresql).
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call
from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory


class TestRepositoryFactory:
    """Test cases for RepositoryFactory"""

    def test_get_environment_config_delegates_to_utils(self):
        """Test that get_environment_config calls the utility function"""
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.get_repository_config') as mock_config:
            mock_config.return_value = {'environment': 'test', 'database_type': 'sqlite'}
            
            result = RepositoryFactory.get_environment_config()
            
            assert result == {'environment': 'test', 'database_type': 'sqlite'}
            mock_config.assert_called_once()

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_task_repository_test_environment(self, mock_config):
        """Test task repository creation for test environment"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockTaskRepository
            
            repo = RepositoryFactory.get_task_repository()
            
            assert isinstance(repo, MockTaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using MockTaskRepository for test environment")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_task_repository_sqlite(self, mock_config):
        """Test task repository creation for SQLite database"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
            
            repo = RepositoryFactory.get_task_repository(
                project_id='proj-123',
                git_branch_name='main',
                user_id='user-456'
            )
            
            assert isinstance(repo, ORMTaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] SQLite configured, using ORMTaskRepository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_task_repository_supabase(self, mock_config):
        """Test task repository creation for Supabase"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'supabase',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
            
            repo = RepositoryFactory.get_task_repository()
            
            assert isinstance(repo, ORMTaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Supabase configured, using ORMTaskRepository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_task_repository_postgresql(self, mock_config):
        """Test task repository creation for PostgreSQL"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'postgresql',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
            
            repo = RepositoryFactory.get_task_repository()
            
            assert isinstance(repo, ORMTaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] PostgreSQL configured, using ORMTaskRepository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_task_repository_unknown_database_exits(self, mock_config):
        """Test that unknown database type causes system exit"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'unknown_db',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            with patch('sys.exit') as mock_exit:
                RepositoryFactory.get_task_repository()
                
                mock_exit.assert_called_once_with(1)
                error_call = mock_logger.error.call_args[0][0]
                assert "CRITICAL: Failed to create repository" in error_call
                assert "unknown_db" in error_call
                assert "NO FALLBACK ALLOWED" in error_call

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_project_repository_test_environment(self, mock_config):
        """Test project repository creation for test environment"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockProjectRepository
            
            repo = RepositoryFactory.get_project_repository()
            
            assert isinstance(repo, MockProjectRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using MockProjectRepository for test environment")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_project_repository_with_cache(self, mock_config):
        """Test project repository with caching enabled"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'sqlite',
            'redis_enabled': True,
            'use_cache': True
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.cached.cached_project_repository import CachedProjectRepository
            from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
            
            repo = RepositoryFactory.get_project_repository()
            
            assert isinstance(repo, CachedProjectRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Wrapping with CachedProjectRepository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_project_repository_cache_import_error(self, mock_config):
        """Test project repository when cache import fails"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'sqlite',
            'redis_enabled': True,
            'use_cache': True
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            with patch.dict('sys.modules', {'agenthub_main.src.fastmcp.task_management.infrastructure.repositories.cached.cached_project_repository': None}):
                from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
                
                repo = RepositoryFactory.get_project_repository()
                
                assert isinstance(repo, ORMProjectRepository)
                mock_logger.warning.assert_any_call("CachedProjectRepository not available, using base repository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_git_branch_repository_all_types(self, mock_config):
        """Test git branch repository creation for all database types"""
        db_types = ['sqlite', 'supabase', 'postgresql']
        
        for db_type in db_types:
            mock_config.return_value = {
                'environment': 'production',
                'database_type': db_type,
                'redis_enabled': False,
                'use_cache': False
            }
            
            with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
                from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
                
                repo = RepositoryFactory.get_git_branch_repository(user_id='user-789')
                
                assert isinstance(repo, ORMGitBranchRepository)
                expected_msg = f"[RepositoryFactory] {db_type.capitalize()} configured, using ORMGitBranchRepository"
                if db_type == 'sqlite':
                    expected_msg = "[RepositoryFactory] SQLite configured, using ORMGitBranchRepository"
                elif db_type == 'supabase':
                    expected_msg = "[RepositoryFactory] Supabase configured, using ORMGitBranchRepository"
                elif db_type == 'postgresql':
                    expected_msg = "[RepositoryFactory] PostgreSQL configured, using ORMGitBranchRepository"
                
                mock_logger.info.assert_any_call(expected_msg)

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_subtask_repository_test_environment(self, mock_config):
        """Test subtask repository creation for test environment"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockSubtaskRepository
            
            repo = RepositoryFactory.get_subtask_repository(user_id='user-123')
            
            assert isinstance(repo, MockSubtaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using MockSubtaskRepository for test environment")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_agent_repository_test_environment(self, mock_config):
        """Test agent repository creation for test environment"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockAgentRepository
            
            repo = RepositoryFactory.get_agent_repository()
            
            assert isinstance(repo, MockAgentRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using MockAgentRepository for test environment")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_context_repository_test_environment(self, mock_config):
        """Test context repository creation for test environment"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            # Try MockContextRepository first, fall back to MockTaskContextRepository
            try:
                from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockContextRepository
                expected_type = MockContextRepository
                expected_log = "[RepositoryFactory] Using MockContextRepository for test environment"
            except ImportError:
                from fastmcp.task_management.infrastructure.repositories.mock_task_context_repository import MockTaskContextRepository
                expected_type = MockTaskContextRepository
                expected_log = "MockContextRepository not available, using mock task context"
            
            repo = RepositoryFactory.get_context_repository()
            
            assert isinstance(repo, expected_type)
            if expected_log == "MockContextRepository not available, using mock task context":
                mock_logger.warning.assert_any_call(expected_log)
            else:
                mock_logger.info.assert_any_call(expected_log)

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_get_context_repository_sqlite(self, mock_config):
        """Test context repository creation for SQLite"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'sqlite',
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.get_db_config') as mock_db_config:
                mock_session = MagicMock()
                mock_db_config.return_value.SessionLocal = mock_session
                
                from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
                
                repo = RepositoryFactory.get_context_repository()
                
                assert isinstance(repo, TaskContextRepository)
                mock_logger.info.assert_any_call("[RepositoryFactory] SQLite configured, using TaskContextRepository")

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_caching_disabled_in_test_environment(self, mock_config):
        """Test that caching is never applied in test environment even if enabled"""
        mock_config.return_value = {
            'environment': 'test',
            'database_type': 'sqlite',
            'redis_enabled': True,
            'use_cache': True
        }
        
        # Test all repository types
        repos = [
            RepositoryFactory.get_task_repository,
            RepositoryFactory.get_project_repository,
            RepositoryFactory.get_git_branch_repository,
            RepositoryFactory.get_subtask_repository,
            RepositoryFactory.get_agent_repository,
            RepositoryFactory.get_context_repository
        ]
        
        for repo_func in repos:
            repo = repo_func()
            # Should get mock repositories, not cached ones
            assert 'Mock' in repo.__class__.__name__
            assert 'Cached' not in repo.__class__.__name__

    @patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config')
    def test_fallback_behavior_for_repositories(self, mock_config):
        """Test fallback behavior for repositories without specific database implementations"""
        mock_config.return_value = {
            'environment': 'production',
            'database_type': 'unknown',  # This will trigger fallback for some repos
            'redis_enabled': False,
            'use_cache': False
        }
        
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.logger') as mock_logger:
            # Test project repository fallback
            from fastmcp.task_management.infrastructure.repositories.orm.project_repository import ORMProjectRepository
            repo = RepositoryFactory.get_project_repository()
            assert isinstance(repo, ORMProjectRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using ORMProjectRepository (fallback)")
            
            # Test git branch repository fallback
            from fastmcp.task_management.infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository
            repo = RepositoryFactory.get_git_branch_repository()
            assert isinstance(repo, ORMGitBranchRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using ORMGitBranchRepository (fallback)")
            
            # Test subtask repository fallback
            from fastmcp.task_management.infrastructure.repositories.orm.subtask_repository import ORMSubtaskRepository
            repo = RepositoryFactory.get_subtask_repository(user_id='user-999')
            assert isinstance(repo, ORMSubtaskRepository)
            mock_logger.info.assert_any_call("[RepositoryFactory] Using ORMSubtaskRepository (fallback) with user_id: user-999")

    def test_task_repository_cache_temporarily_disabled(self):
        """Test that task repository caching is temporarily disabled (hardcoded to False)"""
        # This test verifies the TODO comment in the code about async/sync mismatch
        with patch('agenthub_main.src.fastmcp.task_management.infrastructure.repositories.repository_factory.RepositoryFactory.get_environment_config') as mock_config:
            mock_config.return_value = {
                'environment': 'production',
                'database_type': 'sqlite',
                'redis_enabled': True,
                'use_cache': True
            }
            
            from fastmcp.task_management.infrastructure.repositories.orm.task_repository import ORMTaskRepository
            
            repo = RepositoryFactory.get_task_repository()
            
            # Should get ORM repository directly, not cached version
            assert isinstance(repo, ORMTaskRepository)
            assert not hasattr(repo, '__wrapped__')  # Cached repos have this attribute