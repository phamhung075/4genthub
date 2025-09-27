"""
Tests for ContextHierarchyValidator

Tests the validation logic for context hierarchy requirements and user-friendly guidance.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Tuple

from fastmcp.task_management.application.services.context_hierarchy_validator import ContextHierarchyValidator
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel
from fastmcp.task_management.infrastructure.database.models import GLOBAL_SINGLETON_UUID


class TestContextHierarchyValidator:
    """Test suite for ContextHierarchyValidator"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_global_repo = Mock()
        self.mock_project_repo = Mock()
        self.mock_branch_repo = Mock()
        self.mock_task_repo = Mock()
        self.user_id = "test-user-123"
        
        self.validator = ContextHierarchyValidator(
            global_repo=self.mock_global_repo,
            project_repo=self.mock_project_repo,
            branch_repo=self.mock_branch_repo,
            task_repo=self.mock_task_repo,
            user_id=self.user_id
        )

    def test_initialization(self):
        """Test validator initialization"""
        # Act & Assert
        assert self.validator.global_repo == self.mock_global_repo
        assert self.validator.project_repo == self.mock_project_repo
        assert self.validator.branch_repo == self.mock_branch_repo
        assert self.validator.task_repo == self.mock_task_repo
        assert self.validator.user_id == self.user_id

    def test_validate_global_context_always_valid(self):
        """Test that global context validation always succeeds"""
        # Arrange
        context_data = {"autonomous_rules": {}}
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.GLOBAL, "global_singleton", context_data
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None

    def test_validate_project_context_success_with_existing_global(self):
        """Test project context validation succeeds when global context exists"""
        # Arrange
        project_id = "test-project-123"
        mock_global_context = Mock()
        self.mock_global_repo.get.return_value = mock_global_context
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.PROJECT, project_id, {}
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None
        self.mock_global_repo.get.assert_called()

    def test_validate_project_context_allows_with_auto_creation_when_global_missing(self):
        """Test project context validation allows creation with auto-creation when global context doesn't exist"""
        # Arrange
        project_id = "test-project-123"
        # Mock global context not found with user-specific ID
        self.mock_global_repo.get.side_effect = [None, None]  # Both user-specific and standard fail
        self.mock_global_repo.list.return_value = []  # No global contexts found
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.PROJECT, project_id, {}
        )
        
        # Assert
        assert is_valid is True  # Now allows creation with auto-creation
        assert error_message is None
        assert guidance is not None
        assert guidance["warning"] == "Global context will be auto-created"
        assert "auto_creation" in guidance
        assert guidance["auto_creation"] is True

    def test_validate_project_context_finds_any_global_context_for_user(self):
        """Test project context validation finds any global context for user when specific one not found"""
        # Arrange
        project_id = "test-project-123"
        mock_global_context = Mock()
        # First two calls return None (user-specific and standard), list returns contexts
        self.mock_global_repo.get.side_effect = [None, None]
        self.mock_global_repo.list.return_value = [mock_global_context]
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.PROJECT, project_id, {}
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None

    def test_validate_branch_context_missing_project_id(self):
        """Test branch context validation fails when project_id is missing and auto-resolve fails"""
        # Arrange
        branch_id = "test-branch-123"
        data = {}  # No project_id
        # Mock branch_repo.get to return None (branch not found)
        self.mock_branch_repo.get.return_value = None
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.BRANCH, branch_id, data
        )
        
        # Assert
        assert is_valid is False
        assert "Branch context requires project_id" in error_message
        assert guidance is not None
        assert guidance["error"] == "Missing required field: project_id"
        assert "auto_resolution_failed" in guidance

    def test_validate_branch_context_success_with_existing_project(self):
        """Test branch context validation succeeds when project context exists"""
        # Arrange
        branch_id = "test-branch-123"
        project_id = "test-project-123"
        data = {"project_id": project_id}
        mock_project_context = Mock()
        self.mock_project_repo.get.return_value = mock_project_context
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.BRANCH, branch_id, data
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None
        self.mock_project_repo.get.assert_called_once_with(project_id)

    def test_validate_branch_context_allows_with_nonexistent_project(self):
        """Test branch context validation allows creation with auto-creation when project context doesn't exist"""
        # Arrange
        branch_id = "test-branch-123"
        project_id = "nonexistent-project"
        data = {"project_id": project_id}
        self.mock_project_repo.get.return_value = None
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.BRANCH, branch_id, data
        )
        
        # Assert
        assert is_valid is True  # Now allows with auto-creation
        assert error_message is None
        assert guidance is not None
        assert f"Parent project context '{project_id}' will be auto-created" in guidance["warning"]
        assert guidance["auto_creation"] is True

    def test_validate_task_context_missing_branch_id(self):
        """Test task context validation fails when branch_id is missing"""
        # Arrange
        task_id = "test-task-123"
        data = {}  # No branch_id
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is False
        assert "Missing required field: branch_id" in error_message
        assert guidance is not None
        assert "required_fields" in guidance
        assert "alternative_names" in guidance["required_fields"]

    def test_validate_task_context_success_with_existing_branch(self):
        """Test task context validation succeeds when branch context exists"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        data = {"branch_id": branch_id}
        mock_branch_context = Mock()
        self.mock_branch_repo.get.return_value = mock_branch_context
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None
        self.mock_branch_repo.get.assert_called_once_with(branch_id)

    def test_validate_task_context_accepts_alternative_field_names(self):
        """Test task context validation accepts alternative branch ID field names"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        mock_branch_context = Mock()
        self.mock_branch_repo.get.return_value = mock_branch_context
        
        test_cases = [
            {"parent_branch_id": branch_id},
            {"git_branch_id": branch_id},
            {"branch_id": branch_id}
        ]
        
        for data in test_cases:
            # Act
            is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
                ContextLevel.TASK, task_id, data
            )
            
            # Assert
            assert is_valid is True, f"Failed for data: {data}"
            assert error_message is None
            assert guidance is None

    def test_validate_task_context_branch_not_found_allows_with_auto_creation(self):
        """Test task context validation allows creation with auto-creation when branch not found"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        data = {"branch_id": branch_id}
        
        # Mock branch_repo.get() returns None (branch not found)
        self.mock_branch_repo.get.return_value = None
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True  # Now allows with auto-creation
        assert error_message is None
        assert guidance is not None
        assert guidance["auto_creation"] is True
        assert f"Parent branch context '{branch_id}' will be auto-created" in guidance["warning"]
        self.mock_branch_repo.get.assert_called_once_with(branch_id)

    def test_validate_task_context_branch_exists(self):
        """Test task context validation succeeds when branch exists"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        data = {"branch_id": branch_id}
        
        # Mock branch_repo.get() returns a valid branch
        mock_branch = Mock()
        mock_branch.project_id = "test-project-123"
        self.mock_branch_repo.get.return_value = mock_branch
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True
        assert error_message is None
        assert guidance is None  # No warnings when branch exists

    def test_validate_task_context_allows_with_nonexistent_branch(self):
        """Test task context validation allows creation with auto-creation for nonexistent branch"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "nonexistent-branch"
        data = {"branch_id": branch_id, "project_id": "test-project"}
        
        # Mock branch_repo.get() returns None
        self.mock_branch_repo.get.return_value = None
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True  # Now allows with auto-creation
        assert error_message is None
        assert guidance is not None
        assert guidance["auto_creation"] is True
        assert "context_creation_order" in guidance
        assert len(guidance["context_creation_order"]) > 0

    def test_validate_unknown_context_level(self):
        """Test validation with unknown context level"""
        # Arrange
        unknown_level = "unknown_level"
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            unknown_level, "test-id", {}
        )
        
        # Assert
        assert is_valid is False
        assert f"Unknown context level: {unknown_level}" in error_message
        assert guidance is None

    def test_get_hierarchy_status_complete(self):
        """Test getting complete hierarchy status"""
        # Arrange
        mock_global_context = Mock()
        self.mock_global_repo.get.return_value = mock_global_context
        self.mock_project_repo.list.return_value = ["project1", "project2"]
        self.mock_branch_repo.list.return_value = ["branch1"]
        self.mock_task_repo.list.return_value = ["task1", "task2", "task3"]
        
        # Act
        status = self.validator.get_hierarchy_status()
        
        # Assert
        assert "hierarchy_levels" in status
        assert status["hierarchy_levels"] == ["global", "project", "branch", "task"]
        assert "current_state" in status
        
        # Check global context
        assert status["current_state"]["global"]["exists"] is True
        assert status["current_state"]["global"]["id"] == "global_singleton"
        
        # Check counts
        assert status["current_state"]["projects"]["count"] == 2
        assert status["current_state"]["branches"]["count"] == 1
        assert status["current_state"]["tasks"]["count"] == 3

    def test_get_hierarchy_status_with_exceptions(self):
        """Test hierarchy status with repository exceptions"""
        # Arrange
        self.mock_global_repo.get.side_effect = Exception("Global repo error")
        self.mock_project_repo.list.side_effect = Exception("Project repo error")
        self.mock_branch_repo.list.side_effect = Exception("Branch repo error")
        self.mock_task_repo.list.side_effect = Exception("Task repo error")
        
        # Act
        status = self.validator.get_hierarchy_status()
        
        # Assert
        assert status["current_state"]["global"]["exists"] is False
        assert status["current_state"]["projects"]["count"] == 0
        assert status["current_state"]["branches"]["count"] == 0
        assert status["current_state"]["tasks"]["count"] == 0

    def test_validate_project_context_without_user_id(self):
        """Test project context validation without user_id"""
        # Arrange
        validator_no_user = ContextHierarchyValidator(
            global_repo=self.mock_global_repo,
            project_repo=self.mock_project_repo,
            branch_repo=self.mock_branch_repo,
            task_repo=self.mock_task_repo,
            user_id=None
        )
        project_id = "test-project-123"
        mock_global_context = Mock()
        self.mock_global_repo.get.return_value = mock_global_context
        
        # Act
        is_valid, error_message, guidance = validator_no_user.validate_hierarchy_requirements(
            ContextLevel.PROJECT, project_id, {}
        )
        
        # Assert
        assert is_valid is True
        # Should only call with standard global singleton UUID
        self.mock_global_repo.get.assert_called_once_with(GLOBAL_SINGLETON_UUID)

    def test_validate_branch_context_with_exception_handling(self):
        """Test branch context validation with exception handling"""
        # Arrange
        branch_id = "test-branch-123"
        project_id = "test-project-123"
        data = {"project_id": project_id}
        self.mock_project_repo.get.side_effect = Exception("Database error")
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.BRANCH, branch_id, data
        )
        
        # Assert
        assert is_valid is False
        assert "Project context must exist first" in error_message
        assert guidance is not None
        assert f"Cannot verify project context: {project_id}" in guidance["error"]

    def test_validate_task_context_with_exception_handling(self):
        """Test task context validation handles repository exceptions gracefully with auto-creation"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        data = {"branch_id": branch_id}
        self.mock_branch_repo.get.side_effect = Exception("Database error")
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True  # Now allows with auto-creation even on exceptions
        assert error_message is None
        assert guidance is not None
        assert guidance["auto_creation"] is True
        assert "Cannot verify branch context" in guidance["warning"]


# Edge cases and error handling tests
class TestContextHierarchyValidatorEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_repos = {
            'global': Mock(),
            'project': Mock(),
            'branch': Mock(),
            'task': Mock()
        }
        
        self.validator = ContextHierarchyValidator(
            global_repo=self.mock_repos['global'],
            project_repo=self.mock_repos['project'],
            branch_repo=self.mock_repos['branch'],
            task_repo=self.mock_repos['task']
        )

    def test_validate_branch_context_alternative_project_id_fields(self):
        """Test branch context validation with alternative project_id field names"""
        # Arrange
        branch_id = "test-branch-123"
        project_id = "test-project-123"
        mock_project_context = Mock()
        self.mock_repos['project'].get.return_value = mock_project_context
        
        test_cases = [
            {"project_id": project_id},
            {"parent_project_id": project_id}
        ]
        
        for data in test_cases:
            # Act
            is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
                ContextLevel.BRANCH, branch_id, data
            )
            
            # Assert
            assert is_valid is True, f"Failed for data: {data}"
            assert error_message is None
            assert guidance is None

    def test_validate_task_context_find_by_id_with_different_signatures(self):
        """Test task context validation with different find_by_id method signatures"""
        # Arrange
        task_id = "test-task-123"
        branch_id = "test-branch-123"
        data = {"branch_id": branch_id}
        
        self.mock_repos['branch'].get.return_value = None
        
        # Mock find_by_id with single parameter signature (just branch_id)
        def mock_find_by_id(branch_id):
            return Mock() if branch_id == "test-branch-123" else None
            
        self.mock_repos['branch'].find_by_id = mock_find_by_id
        # Remove exists method to force find_by_id path
        if hasattr(self.mock_repos['branch'], 'exists'):
            del self.mock_repos['branch'].exists
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.TASK, task_id, data
        )
        
        # Assert
        assert is_valid is True

    def test_empty_context_ids_and_data(self):
        """Test validation with empty context IDs and data"""
        # Test empty context ID
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.PROJECT, "", {}
        )
        
        # Should still attempt validation (empty string is valid context_id technically)
        assert isinstance(is_valid, bool)

    def test_none_context_data(self):
        """Test validation with None context data"""
        # Arrange
        branch_id = "test-branch-123"
        # Mock branch_repo.get to return None (branch not found)
        self.mock_repos['branch'].get.return_value = None
        
        # Act
        is_valid, error_message, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.BRANCH, branch_id, None
        )
        
        # Assert
        # Should handle None data gracefully (converted to empty dict internally)
        assert is_valid is False  # Will fail due to missing project_id
        assert "project_id" in error_message or "Branch context requires project_id" in error_message

    def test_repository_none_handling(self):
        """Test validation with None repositories"""
        # Arrange
        validator_with_none_repos = ContextHierarchyValidator(
            global_repo=None,
            project_repo=None,
            branch_repo=None,
            task_repo=None
        )
        
        # Act
        is_valid, error_message, guidance = validator_with_none_repos.validate_hierarchy_requirements(
            ContextLevel.PROJECT, "test-project", {}
        )
        
        # Assert
        # Should handle None repository gracefully - now allows with auto-creation
        assert is_valid is True  # Now returns True with auto-creation warning