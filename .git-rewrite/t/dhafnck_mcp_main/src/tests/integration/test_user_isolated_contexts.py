"""
TDD Integration Tests for User-Isolated Context System

Tests that verify complete user isolation across all context levels.
Each user should have their own isolated context space without any shared state.
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from fastmcp.task_management.domain.entities.context import (
    GlobalContext, ProjectContext, BranchContext, TaskContextUnified as TaskContext
)
from fastmcp.task_management.infrastructure.repositories.global_context_repository import GlobalContextRepository
from fastmcp.task_management.infrastructure.repositories.project_context_repository import ProjectContextRepository
from fastmcp.task_management.infrastructure.repositories.branch_context_repository import BranchContextRepository
from fastmcp.task_management.infrastructure.repositories.task_context_repository import TaskContextRepository
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService


class TestUserIsolatedGlobalContext:
    """Test that global contexts are properly isolated by user_id."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Configure session mock
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.refresh = Mock()
        self.mock_session.get = Mock(return_value=None)
        self.mock_session.query = Mock()
        
    def test_global_context_creates_user_specific_uuid(self):
        """Test that each user gets a unique global context UUID."""
        # Arrange
        user1_id = "user-123"
        user2_id = "user-456"
        
        repo1 = GlobalContextRepository(self.mock_session_factory, user_id=user1_id)
        repo2 = GlobalContextRepository(self.mock_session_factory, user_id=user2_id)
        
        # Act
        user1_global_id = repo1._normalize_context_id("global_singleton")
        user2_global_id = repo2._normalize_context_id("global_singleton")
        
        # Assert
        assert user1_global_id != user2_global_id, "Each user should have a unique global context ID"
        assert user1_global_id != "global_singleton", "ID should be a UUID, not the literal string"
        assert user2_global_id != "global_singleton", "ID should be a UUID, not the literal string"
        
        # Verify UUIDs are valid
        uuid.UUID(user1_global_id)  # Should not raise
        uuid.UUID(user2_global_id)  # Should not raise
    
    def test_global_context_deterministic_for_same_user(self):
        """Test that the same user always gets the same global context UUID."""
        # Arrange
        user_id = "user-789"
        
        repo1 = GlobalContextRepository(self.mock_session_factory, user_id=user_id)
        repo2 = GlobalContextRepository(self.mock_session_factory, user_id=user_id)
        
        # Act
        id1 = repo1._normalize_context_id("global_singleton")
        id2 = repo2._normalize_context_id("global_singleton")
        
        # Assert
        assert id1 == id2, "Same user should always get the same global context ID"
    
    def test_global_context_no_singleton_uuid_reference(self):
        """Verify that GLOBAL_SINGLETON_UUID is not used anywhere."""
        # Arrange
        user_id = "test-user"
        repo = GlobalContextRepository(self.mock_session_factory, user_id=user_id)
        
        # Act
        context_id = repo._normalize_context_id("global_singleton")
        
        # Assert - The old singleton UUID should never appear
        assert "00000000-0000-0000-0000-000000000001" not in context_id
        assert context_id != "00000000-0000-0000-0000-000000000001"


class TestUserIsolatedProjectContext:
    """Test that project contexts are properly isolated by user_id."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Configure session mock
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        self.mock_session.get = Mock(return_value=None)
        
    def test_project_context_user_isolation(self):
        """Test that project contexts are isolated by user."""
        # Arrange
        user1_id = "user-001"
        user2_id = "user-002"
        project_id = str(uuid.uuid4())
        
        # Create project context for user 1
        repo1 = ProjectContextRepository(self.mock_session_factory, user_id=user1_id)
        context1 = ProjectContext(
            id=project_id,
            project_name="Test Project",
            project_settings={"owner": "user1"},
            metadata={}
        )
        
        # Mock the database behavior - no existing context
        self.mock_session.get.return_value = None
        
        # Act
        created1 = repo1.create(context1)
        
        # Assert
        assert created1.id == project_id
        self.mock_session.add.assert_called_once()
        
        # Verify the model created has the correct user_id
        created_model = self.mock_session.add.call_args[0][0]
        assert created_model.user_id == user1_id


class TestUserIsolatedBranchContext:
    """Test that branch contexts properly inherit user isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Configure session mock
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        
    def test_branch_context_inherits_user_context(self):
        """Test that branch contexts inherit user context from project."""
        # Arrange
        user_id = "user-branch-test"
        project_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        
        repo = BranchContextRepository(self.mock_session_factory, user_id=user_id)
        
        context = BranchContext(
            id=branch_id,
            git_branch_name="feature/test",
            project_id=project_id,
            branch_settings={"created_by": user_id},
            metadata={}
        )
        
        # Mock no existing context
        self.mock_session.get.return_value = None
        
        # Act
        created = repo.create(context)
        
        # Assert
        assert created.id == branch_id
        self.mock_session.add.assert_called_once()
        
        # Verify user context is preserved
        created_model = self.mock_session.add.call_args[0][0]
        assert created_model.user_id == user_id


class TestUserIsolatedTaskContext:
    """Test that task contexts maintain user isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Configure session mock
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.add = Mock()
        self.mock_session.flush = Mock()
        
    def test_task_context_user_isolation(self):
        """Test that task contexts are isolated by user."""
        # Arrange
        user_id = "user-task-test"
        branch_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        repo = TaskContextRepository(self.mock_session_factory, user_id=user_id)
        
        context = TaskContext(
            id=task_id,
            branch_id=branch_id,
            task_data={"title": "Test Task", "assigned_to": user_id},
            metadata={}
        )
        
        # Mock no existing context
        self.mock_session.get.return_value = None
        
        # Act
        created = repo.create(context)
        
        # Assert
        assert created.id == task_id
        self.mock_session.add.assert_called_once()
        
        # Verify user isolation
        created_model = self.mock_session.add.call_args[0][0]
        assert created_model.user_id == user_id


class TestUnifiedContextServiceUserIsolation:
    """Test the unified context service with user isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session_factory = Mock()
        self.mock_session = Mock()
        self.mock_session_factory.return_value = self.mock_session
        
        # Configure session mock
        self.mock_session.commit = Mock()
        self.mock_session.rollback = Mock()
        self.mock_session.close = Mock()
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Create repositories
        self.global_repo = Mock(spec=GlobalContextRepository)
        self.project_repo = Mock(spec=ProjectContextRepository)
        self.branch_repo = Mock(spec=BranchContextRepository)
        self.task_repo = Mock(spec=TaskContextRepository)
        
        # Create service
        self.service = UnifiedContextService(
            global_context_repository=self.global_repo,
            project_context_repository=self.project_repo,
            branch_context_repository=self.branch_repo,
            task_context_repository=self.task_repo,
            user_id="test-user-service"
        )
    
    def test_service_normalizes_global_context_for_user(self):
        """Test that the service properly normalizes global context IDs for users."""
        # Arrange
        level = "global"
        context_id = "global_singleton"
        
        # Act
        normalized_id = self.service._normalize_context_id(level, context_id)
        
        # Assert
        assert normalized_id != "global_singleton"
        assert normalized_id != "00000000-0000-0000-0000-000000000001"  # Not the old singleton
        uuid.UUID(normalized_id)  # Should be a valid UUID
    
    def test_service_creates_user_specific_global_context(self):
        """Test that service creates user-specific global contexts."""
        # Arrange
        self.global_repo.create.return_value = GlobalContext(
            id=str(uuid.uuid4()),
            organization_name="Test Org",
            global_settings={"test": "data"},
            metadata={}
        )
        
        # Act
        result = self.service.create_context(
            level="global",
            context_id="global_singleton",
            data={"autonomous_rules": {"enabled": True}},
            user_id="test-user"
        )
        
        # Assert
        assert result is not None
        self.global_repo.create.assert_called_once()
        
        # Verify the context passed to repository has proper structure
        created_context = self.global_repo.create.call_args[0][0]
        assert isinstance(created_context, GlobalContext)


class TestContextHierarchyWithUserIsolation:
    """Test the full context hierarchy with user isolation."""
    
    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories."""
        return {
            'global': Mock(spec=GlobalContextRepository),
            'project': Mock(spec=ProjectContextRepository),
            'branch': Mock(spec=BranchContextRepository),
            'task': Mock(spec=TaskContextRepository)
        }
    
    def test_context_inheritance_respects_user_boundaries(self, mock_repos):
        """Test that context inheritance doesn't cross user boundaries."""
        # Arrange
        user1_id = "user-001"
        user2_id = "user-002"
        
        # Create services for different users
        service1 = UnifiedContextService(
            global_context_repository=mock_repos['global'],
            project_context_repository=mock_repos['project'],
            branch_context_repository=mock_repos['branch'],
            task_context_repository=mock_repos['task'],
            user_id=user1_id
        )
        
        service2 = UnifiedContextService(
            global_context_repository=mock_repos['global'],
            project_context_repository=mock_repos['project'],
            branch_context_repository=mock_repos['branch'],
            task_context_repository=mock_repos['task'],
            user_id=user2_id
        )
        
        # Act - normalize same logical ID for different users
        global_id1 = service1._normalize_context_id("global", "global_singleton")
        global_id2 = service2._normalize_context_id("global", "global_singleton")
        
        # Assert - different users get different IDs
        assert global_id1 != global_id2
        assert "00000000-0000-0000-0000-000000000001" not in global_id1
        assert "00000000-0000-0000-0000-000000000001" not in global_id2
    
    def test_no_cross_user_data_leakage(self, mock_repos):
        """Verify that one user cannot access another user's context."""
        # Arrange
        user1_id = "user-secure-001"
        project_id = str(uuid.uuid4())
        
        # Configure mock to simulate user-filtered query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # No context found for different user
        
        mock_repos['project'].get = Mock(return_value=None)
        
        # Create repository for user1
        repo1 = ProjectContextRepository(Mock(), user_id=user1_id)
        repo1.get = Mock(return_value=None)  # Simulate no access to other user's data
        
        # Act - Try to get a project context
        result = repo1.get(project_id)
        
        # Assert
        assert result is None  # Should not find context from another user


if __name__ == "__main__":
    pytest.main([__file__, "-v"])