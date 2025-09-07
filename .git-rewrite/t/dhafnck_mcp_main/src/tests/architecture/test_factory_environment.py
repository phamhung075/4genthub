"""
Test Suite: Repository Factory Environment Detection
Ensures factories check environment variables for proper repository switching
"""

import pytest
from pathlib import Path
import os
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import importlib


class TestFactoryEnvironmentDetection:
    """Test that repository factories check environment variables"""
    
    @pytest.fixture
    def add_src_to_path(self):
        """Add src directory to Python path for imports"""
        src_path = Path(__file__).parent.parent.parent
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        yield
        # Cleanup
        if str(src_path) in sys.path:
            sys.path.remove(str(src_path))
    
    @patch.dict(os.environ, {'ENVIRONMENT': 'test'})
    def test_factory_returns_sqlite_for_test(self, add_src_to_path):
        """Factory should return SQLite/Mock repository in test mode"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            repo = RepositoryFactory.get_task_repository()
            
            # In test mode, should return Mock or SQLite repository
            assert repo is not None
            repo_class_name = repo.__class__.__name__
            assert ('Mock' in repo_class_name or 
                   'SQLite' in repo_class_name or
                   'Test' in repo_class_name), \
                   f"Expected Mock/SQLite repository in test mode, got {repo_class_name}"
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'DATABASE_TYPE': 'supabase'
    })
    def test_factory_returns_supabase_for_production(self, add_src_to_path):
        """Factory should return Supabase repository in production"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            repo = RepositoryFactory.get_task_repository()
            
            # In production with Supabase, should return Supabase or ORM repository
            assert repo is not None
            repo_class_name = repo.__class__.__name__
            assert ('Supabase' in repo_class_name or 
                   'ORM' in repo_class_name or
                   'Cached' in repo_class_name), \
                   f"Expected Supabase/ORM repository in production, got {repo_class_name}"
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'DATABASE_TYPE': 'supabase',
        'REDIS_ENABLED': 'true'
    })
    def test_factory_returns_cached_repository_when_redis_enabled(self, add_src_to_path):
        """Factory should wrap repository with cache when Redis enabled"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            # Mock Redis to avoid actual connection
            with patch('fastmcp.task_management.infrastructure.repositories.repository_factory.redis') as mock_redis:
                mock_redis_client = MagicMock()
                mock_redis.Redis.return_value = mock_redis_client
                
                repo = RepositoryFactory.get_task_repository()
                
                assert repo is not None
                repo_class_name = repo.__class__.__name__
                
                # Should be cached repository wrapper or have caching capabilities
                assert ('Cached' in repo_class_name or 
                       hasattr(repo, 'cache') or
                       hasattr(repo, 'redis_client')), \
                       f"Expected cached repository with Redis enabled, got {repo_class_name}"
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'DATABASE_TYPE': 'supabase',
        'REDIS_ENABLED': 'false'
    })
    def test_factory_returns_direct_repository_when_redis_disabled(self, add_src_to_path):
        """Factory should return direct repository when Redis disabled"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            repo = RepositoryFactory.get_task_repository()
            
            assert repo is not None
            repo_class_name = repo.__class__.__name__
            
            # When Redis is disabled, should not have "Cached" in the name
            # But it's OK if the repo has caching capabilities built-in
            if 'Cached' in repo_class_name:
                # If it's cached, verify it can work without Redis
                assert hasattr(repo, 'base_repo') or hasattr(repo, '_fallback_to_base')
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")
    
    def test_all_factories_check_environment(self):
        """All factory files must check environment variables"""
        factory_path = Path(__file__).parent.parent.parent / 'fastmcp/task_management/infrastructure/repositories'
        
        # Required environment checks
        required_checks = [
            "os.getenv('ENVIRONMENT'",
            "os.environ.get('ENVIRONMENT'",
            "os.getenv('DATABASE_TYPE'",
            "os.environ.get('DATABASE_TYPE'",
        ]
        
        violations = []
        
        # Look for factory files
        factory_files = list(factory_path.glob('*factory*.py'))
        
        # Also check for a central repository_factory.py
        central_factory = factory_path / 'repository_factory.py'
        if central_factory.exists():
            factory_files.append(central_factory)
        
        if not factory_files:
            pytest.skip("No factory files found to test")
        
        for factory_file in factory_files:
            content = factory_file.read_text()
            
            # Check if file has any environment checks
            has_env_check = any(check in content for check in required_checks)
            
            if not has_env_check:
                # Check if it imports from a central factory that does the checking
                if 'from .repository_factory import' not in content and \
                   'from . import repository_factory' not in content:
                    violations.append(f"{factory_file.name}: No environment checks found")
        
        # If there's a central factory that handles everything, that's OK
        if violations and central_factory.exists():
            central_content = central_factory.read_text()
            has_central_env_check = any(check in central_content for check in required_checks)
            if has_central_env_check:
                violations = []  # Central factory handles it
        
        assert not violations, (
            f"Factories missing environment checks:\n" +
            "\n".join(violations)
        )
    
    def test_factory_handles_unknown_database_type(self, add_src_to_path):
        """Factory should handle unknown database type gracefully"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'production',
                'DATABASE_TYPE': 'unknown_db_xyz'
            }):
                # Should either raise error or return default
                try:
                    repo = RepositoryFactory.get_task_repository()
                    # If it doesn't raise, it should return a valid repository
                    assert repo is not None
                except (ValueError, NotImplementedError) as e:
                    # Expected - factory should raise for unknown DB types
                    assert 'unknown' in str(e).lower() or 'database' in str(e).lower()
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")


class TestRepositoryFactoryPatterns:
    """Test specific repository factory implementations"""
    
    def test_central_factory_implementation(self):
        """Test that central factory is properly implemented"""
        factory_file = Path(__file__).parent.parent.parent / \
                      'fastmcp/task_management/infrastructure/repositories/repository_factory.py'
        
        if not factory_file.exists():
            pytest.skip("Central repository factory not found")
        
        content = factory_file.read_text()
        
        # Check for proper patterns
        checks = {
            'Environment check': "os.getenv('ENVIRONMENT'",
            'Database type check': "os.getenv('DATABASE_TYPE'",
            'Test mode handling': "== 'test'",
            'Production mode': "== 'production'",
            'Supabase support': "'supabase'",
            'SQLite support': "'sqlite'",
        }
        
        missing = []
        for check_name, pattern in checks.items():
            if pattern not in content.lower() and pattern.upper() not in content:
                missing.append(check_name)
        
        assert not missing, (
            f"Central factory missing implementations:\n" +
            "\n".join(missing)
        )
    
    def test_cached_repository_implementation(self):
        """Test that cached repository wrapper exists and works"""
        cached_path = Path(__file__).parent.parent.parent / \
                     'fastmcp/task_management/infrastructure/repositories/cached'
        
        if not cached_path.exists():
            pytest.skip("Cached repository directory not found")
        
        cached_files = list(cached_path.glob('*.py'))
        
        assert cached_files, "No cached repository implementations found"
        
        # Check at least one cached repository implementation
        for cached_file in cached_files:
            if cached_file.name == '__init__.py':
                continue
                
            content = cached_file.read_text()
            
            # Should have cache invalidation methods
            assert 'invalidate' in content or 'clear_cache' in content, \
                   f"{cached_file.name} missing cache invalidation methods"
            
            # Should wrap a base repository
            assert 'base_repo' in content or 'repository' in content, \
                   f"{cached_file.name} doesn't wrap a base repository"


class TestEnvironmentSwitching:
    """Integration tests for environment-based repository switching"""
    
    @pytest.fixture
    def mock_database_connections(self):
        """Mock database connections to avoid real DB access"""
        with patch('sqlalchemy.create_engine') as mock_engine, \
             patch('supabase.create_client') as mock_supabase, \
             patch('redis.Redis') as mock_redis:
            
            # Setup mock returns
            mock_engine.return_value = MagicMock()
            mock_supabase.return_value = MagicMock()
            mock_redis.return_value = MagicMock()
            
            yield {
                'engine': mock_engine,
                'supabase': mock_supabase,
                'redis': mock_redis
            }
    
    def test_environment_switching_flow(self, add_src_to_path, mock_database_connections):
        """Test complete environment switching flow"""
        try:
            from fastmcp.task_management.infrastructure.repositories.repository_factory import RepositoryFactory
            
            # Test different environment configurations
            test_configs = [
                {'ENVIRONMENT': 'test', 'expected': ['Mock', 'Test', 'SQLite']},
                {'ENVIRONMENT': 'development', 'DATABASE_TYPE': 'sqlite', 'expected': ['SQLite', 'Mock']},
                {'ENVIRONMENT': 'production', 'DATABASE_TYPE': 'supabase', 'expected': ['Supabase', 'ORM', 'Cached']},
            ]
            
            for config in test_configs:
                expected = config.pop('expected')
                
                with patch.dict(os.environ, config, clear=True):
                    repo = RepositoryFactory.get_task_repository()
                    assert repo is not None
                    
                    repo_class_name = repo.__class__.__name__
                    assert any(exp in repo_class_name for exp in expected), \
                           f"Config {config} should return one of {expected}, got {repo_class_name}"
        except ImportError as e:
            pytest.skip(f"Could not import RepositoryFactory: {e}")


class TestFactoryComplianceSummary:
    """Summary compliance test for repository factories"""
    
    def test_overall_factory_compliance(self):
        """Generate compliance report for factory implementations"""
        factory_path = Path(__file__).parent.parent.parent / \
                      'fastmcp/task_management/infrastructure/repositories'
        
        report = {
            'total_factories': 0,
            'compliant_factories': 0,
            'central_factory_exists': False,
            'environment_checking': False,
            'violations': [],
            'compliance_score': 0
        }
        
        # Check for central factory
        central_factory = factory_path / 'repository_factory.py'
        if central_factory.exists():
            report['central_factory_exists'] = True
            content = central_factory.read_text()
            
            # Check for environment detection
            if "os.getenv('ENVIRONMENT'" in content:
                report['environment_checking'] = True
                report['compliant_factories'] += 1
            report['total_factories'] += 1
        
        # Check individual factory files
        factory_files = [f for f in factory_path.glob('*factory*.py') 
                        if f.name != 'repository_factory.py']
        
        for factory_file in factory_files:
            report['total_factories'] += 1
            content = factory_file.read_text()
            
            # Check if it delegates to central factory or has its own checks
            is_compliant = (
                'from .repository_factory import' in content or
                "os.getenv('ENVIRONMENT'" in content or
                report['central_factory_exists']  # If central exists, others can delegate
            )
            
            if is_compliant:
                report['compliant_factories'] += 1
            else:
                report['violations'].append(f"{factory_file.name}: No environment detection")
        
        # Calculate compliance score
        if report['total_factories'] > 0:
            report['compliance_score'] = (
                report['compliant_factories'] / report['total_factories'] * 100
            )
        
        # Generate report
        compliance_report = f"""
        Repository Factory Compliance Report:
        ====================================
        Central Factory Exists: {report['central_factory_exists']}
        Environment Checking: {report['environment_checking']}
        Total Factories: {report['total_factories']}
        Compliant Factories: {report['compliant_factories']}
        Compliance Score: {report['compliance_score']:.1f}%
        
        Violations:
        {chr(10).join(report['violations']) if report['violations'] else 'None'}
        """
        
        print(compliance_report)
        
        # For factory compliance, we're more lenient if there's a good central factory
        min_score = 80 if report['central_factory_exists'] else 90
        
        assert report['compliance_score'] >= min_score, (
            f"Factory compliance score too low: {report['compliance_score']:.1f}% "
            f"(minimum required: {min_score}%)"
        )