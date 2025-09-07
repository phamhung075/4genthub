"""
Test branch context creation with auto-detection of project_id.

This test verifies that when creating a branch context without providing
project_id, the system automatically detects it from the git branch entity.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.application.services.context_hierarchy_validator import ContextHierarchyValidator
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.domain.entities.git_branch import GitBranch


class TestBranchContextAutoDetectProjectId(unittest.TestCase):
    """Test suite for branch context project_id auto-detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock repositories
        self.global_repo = Mock()
        self.project_repo = Mock()
        self.branch_repo = Mock()
        self.task_repo = Mock()
        
        # Create service with mocked dependencies
        self.service = UnifiedContextService(
            global_context_repository=self.global_repo,
            project_context_repository=self.project_repo,
            branch_context_repository=self.branch_repo,
            task_context_repository=self.task_repo
        )
        
        # Test data
        self.branch_id = str(uuid4())
        self.project_id = str(uuid4())
        self.branch_name = "feature/test-branch"
        
    def test_branch_context_creation_without_project_id_auto_detects(self):
        """Test that branch context creation auto-detects project_id from git branch."""
        # Arrange
        # Mock global context exists
        self.global_repo.get.return_value = Mock(id="global_singleton")
        
        # Mock project context exists
        self.project_repo.get.return_value = Mock(id=self.project_id)
        
        # Mock the git branch repository factory
        mock_git_branch = GitBranch(
            id=self.branch_id,
            name=self.branch_name,
            description="Test branch",
            project_id=self.project_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory') as mock_factory:
            mock_git_repo = Mock()
            mock_git_repo.get.return_value = mock_git_branch
            mock_factory.return_value.create.return_value = mock_git_repo
            
            # Mock branch context repository create
            self.branch_repo.create.return_value = Mock(
                id=self.branch_id,
                project_id=self.project_id,
                git_branch_name=self.branch_name
            )
            
            # Act - Create branch context WITHOUT project_id
            result = self.service.create_context(
                level="branch",
                context_id=self.branch_id,
                data={
                    "git_branch_name": self.branch_name,
                    "branch_settings": {}
                }
            )
            
            # Assert
            self.assertTrue(result["success"])
            self.assertEqual(result["context_id"], self.branch_id)
            self.assertEqual(result["level"], "branch")
            
            # Verify git branch was queried for project_id
            mock_git_repo.get.assert_called_once_with(self.branch_id)
            
            # Verify branch context was created with auto-detected project_id
            created_context = self.branch_repo.create.call_args[0][0]
            self.assertEqual(created_context.project_id, self.project_id)
    
    def test_branch_context_creation_with_explicit_project_id_skips_auto_detect(self):
        """Test that explicit project_id is used when provided."""
        # Arrange
        explicit_project_id = str(uuid4())
        
        # Mock global and project contexts exist
        self.global_repo.get.return_value = Mock(id="global_singleton")
        self.project_repo.get.return_value = Mock(id=explicit_project_id)
        
        # Mock branch context repository create
        self.branch_repo.create.return_value = Mock(
            id=self.branch_id,
            project_id=explicit_project_id,
            git_branch_name=self.branch_name
        )
        
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory') as mock_factory:
            # Act - Create branch context WITH explicit project_id
            result = self.service.create_context(
                level="branch",
                context_id=self.branch_id,
                data={
                    "project_id": explicit_project_id,
                    "git_branch_name": self.branch_name,
                    "branch_settings": {}
                }
            )
            
            # Assert
            self.assertTrue(result["success"])
            
            # Verify git branch repository was NOT created (no auto-detection needed)
            mock_factory.assert_not_called()
            
            # Verify branch context was created with explicit project_id
            created_context = self.branch_repo.create.call_args[0][0]
            self.assertEqual(created_context.project_id, explicit_project_id)
    
    def test_branch_context_creation_handles_auto_detect_failure_gracefully(self):
        """Test that branch context creation continues validation when auto-detect fails."""
        # Arrange
        # Mock global context exists but project doesn't
        self.global_repo.get.return_value = Mock(id="global_singleton")
        self.project_repo.get.return_value = None
        
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory') as mock_factory:
            # Make git branch lookup fail
            mock_git_repo = Mock()
            mock_git_repo.get.side_effect = Exception("Git branch not found")
            mock_factory.return_value.create.return_value = mock_git_repo
            
            # Act - Create branch context without project_id and with failed auto-detection
            result = self.service.create_context(
                level="branch",
                context_id=self.branch_id,
                data={
                    "git_branch_name": self.branch_name,
                    "branch_settings": {}
                }
            )
            
            # Assert
            self.assertFalse(result["success"])
            self.assertIn("project_id", result["error"])
            self.assertIn("auto-detected", result.get("explanation", ""))
    
    def test_branch_context_auto_detect_with_async_repository(self):
        """Test auto-detection works with async git branch repository."""
        import asyncio
        
        # Arrange
        # Mock global and project contexts exist
        self.global_repo.get.return_value = Mock(id="global_singleton")
        self.project_repo.get.return_value = Mock(id=self.project_id)
        
        # Mock async git branch
        mock_git_branch = GitBranch(
            id=self.branch_id,
            name=self.branch_name,
            description="Test branch",
            project_id=self.project_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        async def mock_find_by_id(project_id, branch_id):
            return mock_git_branch
        
        with patch('fastmcp.task_management.infrastructure.repositories.git_branch_repository_factory.GitBranchRepositoryFactory') as mock_factory:
            # Mock async repository (no 'get' method, only async 'find_by_id')
            mock_git_repo = Mock()
            del mock_git_repo.get  # Remove default mock method
            mock_git_repo.find_by_id = mock_find_by_id
            mock_factory.return_value.create.return_value = mock_git_repo
            
            # Mock branch context repository create
            self.branch_repo.create.return_value = Mock(
                id=self.branch_id,
                project_id=self.project_id,
                git_branch_name=self.branch_name
            )
            
            # Act - Create branch context WITHOUT project_id
            result = self.service.create_context(
                level="branch",
                context_id=self.branch_id,
                data={
                    "git_branch_name": self.branch_name,
                    "branch_settings": {}
                }
            )
            
            # Assert
            self.assertTrue(result["success"])
            
            # Verify branch context was created with auto-detected project_id
            created_context = self.branch_repo.create.call_args[0][0]
            self.assertEqual(created_context.project_id, self.project_id)
    
    def test_hierarchy_validator_shows_auto_detect_message(self):
        """Test that hierarchy validator provides helpful auto-detection message."""
        # Arrange
        validator = ContextHierarchyValidator(
            global_repo=self.global_repo,
            project_repo=self.project_repo,
            branch_repo=self.branch_repo,
            task_repo=self.task_repo
        )
        
        # Act - Validate branch without project_id
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id=self.branch_id,
            data={"git_branch_name": self.branch_name}
        )
        
        # Assert
        self.assertFalse(is_valid)
        self.assertIn("auto-detected", guidance["explanation"])
        self.assertIn("auto_detection", guidance)
        self.assertIn("example", guidance)
        self.assertNotIn("project_id", guidance["example"])  # Example without project_id


if __name__ == "__main__":
    unittest.main()