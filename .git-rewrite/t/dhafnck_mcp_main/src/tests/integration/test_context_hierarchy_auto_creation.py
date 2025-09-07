"""
Integration Tests for Context Hierarchy Auto-Creation

Tests the enhanced auto-creation functionality that automatically creates
missing parent contexts when creating branch or task contexts.
"""

import pytest
import uuid
import logging
from unittest.mock import MagicMock, patch

from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.domain.entities.context import (
    GlobalContext, ProjectContext, BranchContext, TaskContextUnified as TaskContext
)

# Set up logging for test debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestContextHierarchyAutoCreation:
    """Test cases for context hierarchy auto-creation functionality."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing."""
        global_repo = MagicMock()
        project_repo = MagicMock()
        branch_repo = MagicMock()
        task_repo = MagicMock()
        
        return {
            'global': global_repo,
            'project': project_repo,
            'branch': branch_repo,
            'task': task_repo
        }

    @pytest.fixture
    def unified_context_service(self, mock_repositories):
        """Create UnifiedContextService with mocked dependencies."""
        service = UnifiedContextService(
            global_context_repository=mock_repositories['global'],
            project_context_repository=mock_repositories['project'],
            branch_context_repository=mock_repositories['branch'],
            task_context_repository=mock_repositories['task']
        )
        return service

    def test_create_context_atomically_global_context(self, unified_context_service, mock_repositories):
        """Test atomic creation of global context."""
        # Arrange
        global_repo = mock_repositories['global']
        global_repo.get.side_effect = Exception("Context not found")  # Simulate context doesn't exist
        global_repo.create.return_value = GlobalContext(
            id="global_singleton",
            organization_name="Test Org",
            global_settings={},
            metadata={}
        )

        # Act
        success = unified_context_service._create_context_atomically(
            level=ContextLevel.GLOBAL,
            context_id="global_singleton",
            data={}
        )

        # Assert
        assert success is True
        global_repo.get.assert_called_once_with("global_singleton")
        global_repo.create.assert_called_once()

    def test_create_context_atomically_project_context(self, unified_context_service, mock_repositories):
        """Test atomic creation of project context."""
        # Arrange
        project_id = str(uuid.uuid4())
        project_repo = mock_repositories['project']
        project_repo.get.side_effect = Exception("Context not found")  # Simulate context doesn't exist
        project_repo.create.return_value = ProjectContext(
            id=project_id,
            project_name="Test Project",
            project_settings={},
            metadata={}
        )

        # Act
        success = unified_context_service._create_context_atomically(
            level=ContextLevel.PROJECT,
            context_id=project_id,
            data={"project_name": "Test Project"}
        )

        # Assert
        assert success is True
        project_repo.get.assert_called_once_with(project_id)
        project_repo.create.assert_called_once()

    def test_create_context_atomically_already_exists(self, unified_context_service, mock_repositories):
        """Test atomic creation when context already exists."""
        # Arrange
        project_id = str(uuid.uuid4())
        project_repo = mock_repositories['project']
        existing_context = ProjectContext(
            id=project_id,
            project_name="Existing Project",
            project_settings={},
            metadata={}
        )
        project_repo.get.return_value = existing_context

        # Act
        success = unified_context_service._create_context_atomically(
            level=ContextLevel.PROJECT,
            context_id=project_id,
            data={"project_name": "Test Project"}
        )

        # Assert
        assert success is True
        project_repo.get.assert_called_once_with(project_id)
        project_repo.create.assert_not_called()  # Should not create if already exists

    def test_create_hierarchy_atomically_branch_contexts(self, unified_context_service, mock_repositories):
        """Test atomic creation of hierarchy for branch context."""
        # Arrange
        project_id = str(uuid.uuid4())
        global_repo = mock_repositories['global']
        project_repo = mock_repositories['project']
        
        # Mock global context doesn't exist, then gets created
        global_repo.get.side_effect = [Exception("Not found"), GlobalContext(
            id="global_singleton", organization_name="Test Org", global_settings={}, metadata={}
        )]
        global_repo.create.return_value = GlobalContext(
            id="global_singleton", organization_name="Default Organization", global_settings={}, metadata={}
        )
        
        # Mock project context doesn't exist, then gets created
        project_repo.get.side_effect = [Exception("Not found"), ProjectContext(
            id=project_id, project_name=f"Auto-created Project {project_id[:8]}", project_settings={}, metadata={}
        )]
        project_repo.create.return_value = ProjectContext(
            id=project_id, project_name=f"Auto-created Project {project_id[:8]}", project_settings={}, metadata={}
        )

        # Act
        contexts_to_create = [
            (ContextLevel.GLOBAL, "global_singleton", {}),
            (ContextLevel.PROJECT, project_id, {"project_name": f"Auto-created Project {project_id[:8]}"})
        ]
        success = unified_context_service._create_hierarchy_atomically(contexts_to_create)

        # Assert
        assert success is True
        assert global_repo.get.call_count >= 1
        assert project_repo.get.call_count >= 1
        global_repo.create.assert_called_once()
        project_repo.create.assert_called_once()

    def test_auto_create_parent_contexts_for_branch(self, unified_context_service, mock_repositories):
        """Test auto-creation of parent contexts for branch creation."""
        # Arrange
        project_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        
        global_repo = mock_repositories['global']
        project_repo = mock_repositories['project']
        
        # Mock contexts don't exist, then get created
        global_repo.get.side_effect = [Exception("Not found")]
        global_repo.create.return_value = GlobalContext(
            id="global_singleton", organization_name="Default Organization", global_settings={}, metadata={}
        )
        
        project_repo.get.side_effect = [Exception("Not found")]
        project_repo.create.return_value = ProjectContext(
            id=project_id, project_name=f"Auto-created Project {project_id[:8]}", project_settings={}, metadata={}
        )

        # Act
        success = unified_context_service._auto_create_parent_contexts(
            target_level=ContextLevel.BRANCH,
            context_id=branch_id,
            data={"project_id": project_id, "git_branch_name": "feature/test"},
            project_id=project_id
        )

        # Assert
        assert success is True
        global_repo.create.assert_called_once()
        project_repo.create.assert_called_once()

    def test_auto_create_parent_contexts_for_task(self, unified_context_service, mock_repositories):
        """Test auto-creation of parent contexts for task creation."""
        # Arrange
        project_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        global_repo = mock_repositories['global']
        project_repo = mock_repositories['project']
        branch_repo = mock_repositories['branch']
        
        # Mock contexts don't exist, then get created
        global_repo.get.side_effect = [Exception("Not found")]
        global_repo.create.return_value = GlobalContext(
            id="global_singleton", organization_name="Default Organization", global_settings={}, metadata={}
        )
        
        project_repo.get.side_effect = [Exception("Not found")]
        project_repo.create.return_value = ProjectContext(
            id=project_id, project_name=f"Auto-created Project {project_id[:8]}", project_settings={}, metadata={}
        )
        
        branch_repo.get.side_effect = [Exception("Not found")]
        branch_repo.create.return_value = BranchContext(
            id=branch_id, project_id=project_id, git_branch_name=f"auto-branch-{branch_id[:8]}", 
            branch_settings={}, metadata={}
        )

        # Mock project_id resolution from branch
        with patch.object(unified_context_service, '_resolve_project_id_from_branch', return_value=project_id):
            # Act
            success = unified_context_service._auto_create_parent_contexts(
                target_level=ContextLevel.TASK,
                context_id=task_id,
                data={"git_branch_id": branch_id, "task_data": {"title": "Test Task"}}
            )

        # Assert
        assert success is True
        global_repo.create.assert_called_once()
        project_repo.create.assert_called_once()
        branch_repo.create.assert_called_once()

    def test_resolve_project_id_from_branch_success(self, unified_context_service):
        """Test successful resolution of project_id from git branch entity."""
        # Arrange
        branch_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        
        mock_git_branch = MagicMock()
        mock_git_branch.project_id = project_id
        
        mock_git_branch_repo = MagicMock()
        mock_git_branch_repo.get.return_value = mock_git_branch
        
        mock_factory = MagicMock()
        mock_factory.create.return_value = mock_git_branch_repo

        # Act
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory', return_value=mock_factory):
            resolved_project_id = unified_context_service._resolve_project_id_from_branch(branch_id)

        # Assert
        assert resolved_project_id == project_id
        mock_factory.create.assert_called_once()
        mock_git_branch_repo.get.assert_called_once_with(branch_id)

    def test_resolve_project_id_from_branch_not_found(self, unified_context_service):
        """Test resolution of project_id when git branch is not found."""
        # Arrange
        branch_id = str(uuid.uuid4())
        
        mock_git_branch_repo = MagicMock()
        mock_git_branch_repo.get.return_value = None
        
        mock_factory = MagicMock()
        mock_factory.create.return_value = mock_git_branch_repo

        # Act
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory', return_value=mock_factory):
            resolved_project_id = unified_context_service._resolve_project_id_from_branch(branch_id)

        # Assert
        assert resolved_project_id is None

    def test_create_context_atomically_handles_repository_error(self, unified_context_service, mock_repositories):
        """Test atomic creation handles repository errors gracefully."""
        # Arrange
        project_id = str(uuid.uuid4())
        project_repo = mock_repositories['project']
        project_repo.get.side_effect = Exception("Context not found")
        project_repo.create.side_effect = Exception("Database error")

        # Act
        success = unified_context_service._create_context_atomically(
            level=ContextLevel.PROJECT,
            context_id=project_id,
            data={"project_name": "Test Project"}
        )

        # Assert
        assert success is False
        project_repo.get.assert_called_once_with(project_id)
        project_repo.create.assert_called_once()

    def test_build_default_context_data_all_levels(self, unified_context_service):
        """Test building default context data for all hierarchy levels."""
        context_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        git_branch_id = str(uuid.uuid4())

        # Test global level
        global_data = unified_context_service._build_default_context_data(
            level="global",
            context_id="global_singleton",
            data={},
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        assert "organization_name" in global_data
        assert "global_settings" in global_data
        assert global_data["metadata"]["auto_created"] is True

        # Test project level
        project_data = unified_context_service._build_default_context_data(
            level="project",
            context_id=context_id,
            data={},
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        assert "project_name" in project_data
        assert "project_settings" in project_data
        assert project_data["metadata"]["auto_created"] is True

        # Test branch level
        branch_data = unified_context_service._build_default_context_data(
            level="branch",
            context_id=context_id,
            data={},
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        assert "project_id" in branch_data
        assert "git_branch_name" in branch_data
        assert "branch_settings" in branch_data
        assert branch_data["metadata"]["auto_created"] is True

        # Test task level
        task_data = unified_context_service._build_default_context_data(
            level="task",
            context_id=context_id,
            data={},
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        assert "branch_id" in task_data
        assert "task_data" in task_data
        assert "progress" in task_data
        assert task_data["metadata"]["auto_created"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])