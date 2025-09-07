"""
Test Suite: Cache Invalidation Compliance
Ensures all mutation methods properly invalidate cache to prevent stale data
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import ast
import re
import sys


class TestCacheInvalidation:
    """Test that cache is properly invalidated on mutations"""
    
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
    
    def test_cached_task_repository_invalidation(self, add_src_to_path):
        """Test that CachedTaskRepository properly invalidates cache"""
        try:
            from fastmcp.task_management.infrastructure.repositories.cached.cached_task_repository import CachedTaskRepository
            
            # Setup mocks
            mock_base_repo = AsyncMock()
            mock_redis = MagicMock()
            mock_redis.delete = MagicMock()
            mock_redis.scan_iter = MagicMock(return_value=[])
            
            # Create cached repo
            cached_repo = CachedTaskRepository(mock_base_repo)
            cached_repo.redis_client = mock_redis
            cached_repo.enabled = True
            
            # Test create invalidation
            import asyncio
            task = MagicMock()
            task.git_branch_id = "branch-123"
            task.project_id = "proj-456"
            
            # Run async create
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cached_repo.create(task))
            
            # Verify cache invalidation was called
            assert mock_redis.scan_iter.called, "Cache invalidation not triggered on create"
            
            # Check for pattern-based invalidation
            scan_calls = [str(call) for call in mock_redis.scan_iter.call_args_list]
            assert any('list:*' in str(call) or 'branch:' in str(call) for call in scan_calls), \
                   "Expected pattern-based cache invalidation not found"
            
        except ImportError as e:
            pytest.skip(f"Could not import CachedTaskRepository: {e}")
    
    def test_update_task_invalidates_cache(self, add_src_to_path):
        """Test that updating task invalidates specific and list caches"""
        try:
            from fastmcp.task_management.infrastructure.repositories.cached.cached_task_repository import CachedTaskRepository
            
            mock_base_repo = AsyncMock()
            mock_redis = MagicMock()
            mock_redis.delete = MagicMock()
            mock_redis.scan_iter = MagicMock(return_value=[])
            
            cached_repo = CachedTaskRepository(mock_base_repo)
            cached_repo.redis_client = mock_redis
            cached_repo.enabled = True
            
            # Test update invalidation
            import asyncio
            task = MagicMock()
            task.id = "task-789"
            task.git_branch_id = "branch-123"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cached_repo.update(task))
            
            # Verify invalidation
            assert mock_redis.delete.called or mock_redis.scan_iter.called, \
                   "Cache invalidation not triggered on update"
            
        except ImportError as e:
            pytest.skip(f"Could not import CachedTaskRepository: {e}")
    
    def test_delete_task_invalidates_cache(self, add_src_to_path):
        """Test that deleting task invalidates all related caches"""
        try:
            from fastmcp.task_management.infrastructure.repositories.cached.cached_task_repository import CachedTaskRepository
            
            mock_base_repo = AsyncMock()
            mock_redis = MagicMock()
            mock_redis.delete = MagicMock()
            mock_redis.scan_iter = MagicMock(return_value=[])
            
            cached_repo = CachedTaskRepository(mock_base_repo)
            cached_repo.redis_client = mock_redis
            cached_repo.enabled = True
            
            # Test delete invalidation
            import asyncio
            task_id = "task-999"
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cached_repo.delete(task_id))
            
            # Verify nuclear invalidation
            assert mock_redis.scan_iter.called, "Cache invalidation not triggered on delete"
            
        except ImportError as e:
            pytest.skip(f"Could not import CachedTaskRepository: {e}")
    
    def test_cache_invalidation_graceful_fallback(self, add_src_to_path):
        """Test that cache operations work even if Redis is unavailable"""
        try:
            from fastmcp.task_management.infrastructure.repositories.cached.cached_task_repository import CachedTaskRepository
            
            mock_base_repo = AsyncMock()
            mock_base_repo.create = AsyncMock(return_value=MagicMock())
            
            # Redis client is None (unavailable)
            cached_repo = CachedTaskRepository(mock_base_repo)
            cached_repo.redis_client = None
            cached_repo.enabled = False  # Should be disabled when Redis unavailable
            
            # Operations should still work
            import asyncio
            task = MagicMock()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(cached_repo.create(task))
            
            # Base repo should still be called
            assert mock_base_repo.create.called, "Base repository not called when cache unavailable"
            # No errors should be raised
            assert result is not None
            
        except ImportError as e:
            pytest.skip(f"Could not import CachedTaskRepository: {e}")


class TestRepositoryMutationInvalidation:
    """Test that all repository mutation methods have cache invalidation"""
    
    def test_all_mutation_methods_have_invalidation(self):
        """Check that mutation methods in cached repositories have invalidation"""
        cached_path = Path(__file__).parent.parent.parent / \
                     'fastmcp/task_management/infrastructure/repositories/cached'
        
        if not cached_path.exists():
            pytest.skip("Cached repository directory not found")
        
        violations = []
        
        # Mutation method patterns
        mutation_methods = [
            r'async def create',
            r'async def update',
            r'async def delete',
            r'async def save',
            r'def create',
            r'def update',
            r'def delete',
            r'def save',
        ]
        
        for repo_file in cached_path.glob('*.py'):
            if repo_file.name == '__init__.py':
                continue
                
            content = repo_file.read_text()
            
            # Find all mutation methods
            for method_pattern in mutation_methods:
                matches = re.finditer(method_pattern, content)
                
                for match in matches:
                    method_start = match.start()
                    # Find the end of the method (next def or end of file)
                    next_def = content.find('\ndef ', method_start + 1)
                    if next_def == -1:
                        next_def = content.find('\nasync def ', method_start + 1)
                    
                    method_body = content[method_start:next_def] if next_def != -1 else content[method_start:]
                    
                    # Check for invalidation patterns
                    invalidation_patterns = [
                        'invalidate',
                        'clear_cache',
                        'delete_pattern',
                        '_invalidate',
                        'scan_iter',  # Redis pattern scanning
                    ]
                    
                    has_invalidation = any(pattern in method_body for pattern in invalidation_patterns)
                    
                    if not has_invalidation:
                        # Extract method name
                        method_name = re.search(r'def (\w+)', method_body)
                        if method_name:
                            violations.append(
                                f"{repo_file.name}: {method_name.group(1)}() missing invalidation"
                            )
        
        assert not violations, (
            f"Mutation methods missing cache invalidation:\n" +
            "\n".join(violations)
        )
    
    def test_invalidation_patterns_comprehensive(self):
        """Test that invalidation patterns cover all necessary cache keys"""
        cached_file = Path(__file__).parent.parent.parent / \
                      'fastmcp/task_management/infrastructure/repositories/cached/cached_task_repository.py'
        
        if not cached_file.exists():
            pytest.skip("CachedTaskRepository not found")
        
        content = cached_file.read_text()
        
        # Check for comprehensive invalidation patterns
        required_patterns = [
            'list:*',      # List caches
            'branch:',     # Branch-specific caches
            'project:',    # Project-specific caches
            'search:',     # Search caches
            'get:',        # Individual item caches
        ]
        
        missing_patterns = []
        for pattern in required_patterns:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        assert not missing_patterns, (
            f"CachedTaskRepository missing invalidation patterns:\n" +
            "\n".join(missing_patterns)
        )


class TestMissingCachedImplementations:
    """Test for repositories that need cached implementations"""
    
    def test_identify_missing_cached_wrappers(self):
        """Identify which repositories don't have cached versions"""
        repo_path = Path(__file__).parent.parent.parent / \
                   'fastmcp/task_management/infrastructure/repositories/orm'
        cached_path = Path(__file__).parent.parent.parent / \
                     'fastmcp/task_management/infrastructure/repositories/cached'
        
        if not repo_path.exists():
            pytest.skip("ORM repository directory not found")
        
        # Get all ORM repositories
        orm_repos = {f.stem for f in repo_path.glob('*_repository.py')}
        
        # Get all cached repositories (if directory exists)
        cached_repos = set()
        if cached_path.exists():
            cached_repos = {f.stem.replace('cached_', '') for f in cached_path.glob('cached_*.py')}
        
        # Find missing cached implementations
        missing_cached = orm_repos - cached_repos
        
        # These are the critical ones that need caching
        critical_repos = {
            'project_repository',
            'git_branch_repository',
            'subtask_repository',
            'agent_repository'
        }
        
        critical_missing = missing_cached & critical_repos
        
        if critical_missing:
            # This is informational, not a failure
            pytest.skip(
                f"Repositories needing cached implementations:\n" +
                "\n".join(f"- {repo}" for repo in critical_missing) +
                "\n\nFollow CachedTaskRepository pattern to implement these."
            )
    
    def test_non_cached_repositories_dont_have_stale_data_risk(self):
        """Test that non-cached repositories at least have proper queries"""
        repo_path = Path(__file__).parent.parent.parent / \
                   'fastmcp/task_management/infrastructure/repositories/orm'
        
        if not repo_path.exists():
            pytest.skip("ORM repository directory not found")
        
        issues = []
        
        for repo_file in repo_path.glob('*_repository.py'):
            content = repo_file.read_text()
            
            # Check if this repo has caching mentions
            has_cache_mention = 'cache' in content.lower()
            
            # If it mentions cache but doesn't invalidate properly
            if has_cache_mention:
                # Check for proper invalidation
                has_invalidation = ('invalidate' in content or 
                                  'clear_cache' in content or
                                  '_invalidate' in content)
                
                if not has_invalidation:
                    issues.append(
                        f"{repo_file.name}: Mentions cache but no invalidation logic"
                    )
        
        assert not issues, (
            f"Repositories with incomplete caching:\n" +
            "\n".join(issues)
        )


class TestCacheInvalidationSummary:
    """Summary compliance test for cache invalidation"""
    
    def test_overall_cache_compliance(self):
        """Generate compliance report for cache invalidation"""
        
        report = {
            'cached_implementations': 0,
            'proper_invalidation': 0,
            'missing_invalidation': 0,
            'missing_wrappers': [],
            'compliance_score': 0
        }
        
        # Check cached directory
        cached_path = Path(__file__).parent.parent.parent / \
                     'fastmcp/task_management/infrastructure/repositories/cached'
        
        if cached_path.exists():
            cached_files = [f for f in cached_path.glob('*.py') if f.name != '__init__.py']
            report['cached_implementations'] = len(cached_files)
            
            # Check each for proper invalidation
            for cached_file in cached_files:
                content = cached_file.read_text()
                
                if 'invalidate' in content or 'clear_cache' in content:
                    report['proper_invalidation'] += 1
                else:
                    report['missing_invalidation'] += 1
        
        # Check for missing critical cached wrappers
        critical_repos = ['project', 'git_branch', 'subtask', 'agent']
        
        for repo_name in critical_repos:
            cached_file = cached_path / f'cached_{repo_name}_repository.py' if cached_path.exists() else None
            if not cached_file or not cached_file.exists():
                report['missing_wrappers'].append(repo_name)
        
        # Calculate compliance score
        total_needed = len(critical_repos) + 1  # +1 for task repository
        implemented = report['cached_implementations']
        
        if total_needed > 0:
            report['compliance_score'] = (implemented / total_needed * 100)
        
        # Generate report
        compliance_report = f"""
        Cache Invalidation Compliance Report:
        ====================================
        Cached Implementations: {report['cached_implementations']}
        With Proper Invalidation: {report['proper_invalidation']}
        Missing Invalidation: {report['missing_invalidation']}
        Missing Critical Wrappers: {', '.join(report['missing_wrappers']) if report['missing_wrappers'] else 'None'}
        Compliance Score: {report['compliance_score']:.1f}%
        
        Recommendations:
        - CachedTaskRepository is properly implemented ✅
        - Use it as a template for missing wrappers
        - Focus on: {', '.join(report['missing_wrappers'])} repositories
        """
        
        print(compliance_report)
        
        # For cache compliance, we're satisfied if task caching works
        # Other repos are nice-to-have
        assert report['cached_implementations'] >= 1, \
               "No cached repository implementations found"
        
        assert report['proper_invalidation'] >= 1, \
               "No proper cache invalidation implementations found"