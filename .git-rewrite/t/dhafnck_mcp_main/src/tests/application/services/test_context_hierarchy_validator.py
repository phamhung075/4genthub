"""Tests for ContextHierarchyValidator"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from fastmcp.task_management.application.services.context_hierarchy_validator import ContextHierarchyValidator
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel


class TestContextHierarchyValidator:
    """Test cases for ContextHierarchyValidator"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_global_repo = Mock()
        self.mock_project_repo = Mock()
        self.mock_branch_repo = Mock()
        self.mock_task_repo = Mock()
        self.user_id = "user-123"
        
        self.validator = ContextHierarchyValidator(
            global_repo=self.mock_global_repo,
            project_repo=self.mock_project_repo,
            branch_repo=self.mock_branch_repo,
            task_repo=self.mock_task_repo,
            user_id=self.user_id
        )

    def test_init(self):
        """Test validator initialization"""
        assert self.validator.global_repo == self.mock_global_repo
        assert self.validator.project_repo == self.mock_project_repo
        assert self.validator.branch_repo == self.mock_branch_repo
        assert self.validator.task_repo == self.mock_task_repo
        assert self.validator.user_id == self.user_id

    def test_init_without_user_id(self):
        """Test validator initialization without user_id"""
        validator = ContextHierarchyValidator(
            global_repo=self.mock_global_repo,
            project_repo=self.mock_project_repo,
            branch_repo=self.mock_branch_repo,
            task_repo=self.mock_task_repo
        )
        
        assert validator.user_id is None

    def test_validate_hierarchy_requirements_global_level(self):
        """Test validation for global level context"""
        is_valid, error, guidance = self.validator.validate_hierarchy_requirements(
            ContextLevel.GLOBAL, "global-id", {}
        )
        
        assert is_valid is True
        assert error is None
        assert guidance is None

    def test_validate_hierarchy_requirements_unknown_level(self):
        """Test validation with unknown level"""
        unknown_level = "unknown_level"
        
        is_valid, error, guidance = self.validator.validate_hierarchy_requirements(
            unknown_level, "context-id", {}
        )
        
        assert is_valid is False
        assert error == f"Unknown context level: {unknown_level}"
        assert guidance is None

    @patch('fastmcp.task_management.application.services.context_hierarchy_validator.GLOBAL_SINGLETON_UUID', 'global-singleton')
    def test_validate_project_requirements_global_exists(self):
        """Test project validation when global context exists"""
        # Setup global context exists
        mock_global_context = Mock()
        self.mock_global_repo.get.return_value = mock_global_context
        
        is_valid, error, guidance = self.validator._validate_project_requirements("project-123")
        
        assert is_valid is True
        assert error is None
        assert guidance is None
        self.mock_global_repo.get.assert_called_once_with('global-singleton')

    @patch('fastmcp.task_management.application.services.context_hierarchy_validator.GLOBAL_SINGLETON_UUID', 'global-singleton')
    def test_validate_project_requirements_global_not_exists_but_found_via_list(self):
        """Test project validation when global context not found by ID but exists via list"""
        # Setup global context not found by ID, but found via list
        self.mock_global_repo.get.return_value = None
        mock_global_context = Mock()
        self.mock_global_repo.list.return_value = [mock_global_context]
        
        is_valid, error, guidance = self.validator._validate_project_requirements("project-123")
        
        assert is_valid is True
        assert error is None
        assert guidance is None
        self.mock_global_repo.get.assert_called_once_with('global-singleton')
        self.mock_global_repo.list.assert_called_once()

    @patch('fastmcp.task_management.application.services.context_hierarchy_validator.GLOBAL_SINGLETON_UUID', 'global-singleton')
    def test_validate_project_requirements_no_global_context(self):
        """Test project validation when no global context exists"""
        # Setup no global context
        self.mock_global_repo.get.return_value = None
        self.mock_global_repo.list.return_value = []
        
        is_valid, error, guidance = self.validator._validate_project_requirements("project-123")
        
        assert is_valid is False
        assert error == "Global context is required before creating project contexts"
        assert guidance is not None
        assert "Cannot create project context without global context" in guidance["error"]
        assert "step_by_step" in guidance
        assert len(guidance["step_by_step"]) == 2

    @patch('fastmcp.task_management.application.services.context_hierarchy_validator.GLOBAL_SINGLETON_UUID', 'global-singleton')
    def test_validate_project_requirements_exception(self):
        """Test project validation when exception occurs"""
        # Setup exception during global context check
        self.mock_global_repo.get.side_effect = Exception("Database error")
        
        is_valid, error, guidance = self.validator._validate_project_requirements("project-123")
        
        assert is_valid is False
        assert error == "Global context must be created first"
        assert guidance is not None
        assert "Global context is required" in guidance["error"]

    def test_validate_branch_requirements_missing_project_id(self):
        """Test branch validation without project_id"""
        branch_id = "branch-123"
        data = {}
        
        is_valid, error, guidance = self.validator._validate_branch_requirements(branch_id, data)
        
        assert is_valid is False
        assert error == "Branch context requires project_id"
        assert guidance is not None
        assert "Missing required field: project_id" in guidance["error"]
        assert "example" in guidance

    def test_validate_branch_requirements_none_data(self):
        """Test branch validation with None data"""
        branch_id = "branch-123"
        data = None
        
        is_valid, error, guidance = self.validator._validate_branch_requirements(branch_id, data)
        
        assert is_valid is False
        assert error == "Branch context requires project_id"

    def test_validate_branch_requirements_project_id_variations(self):
        """Test branch validation with different project_id field names"""
        branch_id = "branch-123"
        project_id = "project-456"
        
        # Test with different field names
        test_cases = [
            {"project_id": project_id},
            {"parent_project_id": project_id}
        ]
        
        for data in test_cases:
            # Setup project context exists
            mock_project_context = Mock()
            self.mock_project_repo.get.return_value = mock_project_context
            
            is_valid, error, guidance = self.validator._validate_branch_requirements(branch_id, data)
            
            assert is_valid is True
            assert error is None
            assert guidance is None
            self.mock_project_repo.get.assert_called_with(project_id)

    def test_validate_branch_requirements_project_not_exists(self):
        """Test branch validation when project context doesn't exist"""
        branch_id = "branch-123"
        project_id = "project-456"
        data = {"project_id": project_id}
        
        # Setup project context doesn't exist
        self.mock_project_repo.get.return_value = None
        
        is_valid, error, guidance = self.validator._validate_branch_requirements(branch_id, data)
        
        assert is_valid is False
        assert error == f"Project context not found: {project_id}"
        assert guidance is not None
        assert f"Parent project context '{project_id}' does not exist" in guidance["error"]
        assert "required_actions" in guidance

    def test_validate_branch_requirements_exception(self):
        """Test branch validation when exception occurs"""
        branch_id = "branch-123"
        project_id = "project-456"
        data = {"project_id": project_id}
        
        # Setup exception during project context check
        self.mock_project_repo.get.side_effect = Exception("Database error")
        
        is_valid, error, guidance = self.validator._validate_branch_requirements(branch_id, data)
        
        assert is_valid is False
        assert error == "Project context must exist first"
        assert guidance is not None

    def test_validate_task_requirements_missing_branch_id(self):
        """Test task validation without branch_id"""
        task_id = "task-123"
        data = {}
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is False
        assert "Missing required field: branch_id" in error
        assert guidance is not None
        assert "alternative_names" in guidance["required_fields"]

    def test_validate_task_requirements_branch_id_variations(self):
        """Test task validation with different branch_id field names"""
        task_id = "task-123"
        branch_id = "branch-456"
        
        # Test with different field names
        test_cases = [
            {"branch_id": branch_id},
            {"parent_branch_id": branch_id},
            {"git_branch_id": branch_id}
        ]
        
        for data in test_cases:
            # Setup branch context exists
            mock_branch_context = Mock()
            self.mock_branch_repo.get.return_value = mock_branch_context
            
            is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
            
            assert is_valid is True
            assert error is None
            assert guidance is None
            self.mock_branch_repo.get.assert_called_with(branch_id)

    def test_validate_task_requirements_branch_not_exists_with_find_by_id(self):
        """Test task validation when branch doesn't exist via get but has find_by_id method"""
        task_id = "task-123"
        branch_id = "branch-456"
        data = {"branch_id": branch_id}
        
        # Setup branch not found via get, but found via find_by_id
        self.mock_branch_repo.get.return_value = None
        mock_branch_context = Mock()
        self.mock_branch_repo.find_by_id = Mock(return_value=mock_branch_context)
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is True
        assert error is None
        assert guidance is None

    def test_validate_task_requirements_branch_exists_via_exists_method(self):
        """Test task validation when branch exists via exists() method"""
        task_id = "task-123"
        branch_id = "branch-456"
        data = {"branch_id": branch_id}
        
        # Setup branch not found via get or find_by_id, but exists via exists()
        self.mock_branch_repo.get.return_value = None
        delattr(self.mock_branch_repo, 'find_by_id') if hasattr(self.mock_branch_repo, 'find_by_id') else None
        self.mock_branch_repo.exists = Mock(return_value=True)
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is True
        assert error is None
        assert guidance is None

    def test_validate_task_requirements_branch_not_exists(self):
        """Test task validation when branch context doesn't exist"""
        task_id = "task-123"
        branch_id = "branch-456"
        data = {"branch_id": branch_id}
        
        # Setup branch context doesn't exist
        self.mock_branch_repo.get.return_value = None
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is False
        assert error == f"Branch context not found: {branch_id}"
        assert guidance is not None
        assert f"Parent branch context '{branch_id}' does not exist" in guidance["error"]
        assert "required_actions" in guidance

    def test_validate_task_requirements_exception(self):
        """Test task validation when exception occurs"""
        task_id = "task-123"
        branch_id = "branch-456"
        data = {"branch_id": branch_id}
        
        # Setup exception during branch context check
        self.mock_branch_repo.get.side_effect = Exception("Database error")
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is False
        assert error == "Branch context must exist first"
        assert guidance is not None

    def test_validate_hierarchy_requirements_project_level(self):
        """Test validation for project level context"""
        with patch.object(self.validator, '_validate_project_requirements') as mock_validate:
            mock_validate.return_value = (True, None, None)
            
            is_valid, error, guidance = self.validator.validate_hierarchy_requirements(
                ContextLevel.PROJECT, "project-123", {}
            )
            
            assert is_valid is True
            mock_validate.assert_called_once_with("project-123")

    def test_validate_hierarchy_requirements_branch_level(self):
        """Test validation for branch level context"""
        data = {"project_id": "project-123"}
        
        with patch.object(self.validator, '_validate_branch_requirements') as mock_validate:
            mock_validate.return_value = (True, None, None)
            
            is_valid, error, guidance = self.validator.validate_hierarchy_requirements(
                ContextLevel.BRANCH, "branch-123", data
            )
            
            assert is_valid is True
            mock_validate.assert_called_once_with("branch-123", data)

    def test_validate_hierarchy_requirements_task_level(self):
        """Test validation for task level context"""
        data = {"branch_id": "branch-123"}
        
        with patch.object(self.validator, '_validate_task_requirements') as mock_validate:
            mock_validate.return_value = (True, None, None)
            
            is_valid, error, guidance = self.validator.validate_hierarchy_requirements(
                ContextLevel.TASK, "task-123", data
            )
            
            assert is_valid is True
            mock_validate.assert_called_once_with("task-123", data)

    def test_get_hierarchy_status_success(self):
        """Test getting hierarchy status successfully"""
        # Setup mock responses
        mock_global_context = Mock()
        self.mock_global_repo.get.return_value = mock_global_context
        self.mock_project_repo.list.return_value = ["proj1", "proj2"]
        self.mock_branch_repo.list.return_value = ["branch1", "branch2", "branch3"]
        self.mock_task_repo.list.return_value = ["task1"]
        
        status = self.validator.get_hierarchy_status()
        
        assert status["hierarchy_levels"] == ["global", "project", "branch", "task"]
        assert status["current_state"]["global"]["exists"] is True
        assert status["current_state"]["global"]["id"] == "global_singleton"
        assert status["current_state"]["projects"]["count"] == 2
        assert status["current_state"]["branches"]["count"] == 3
        assert status["current_state"]["tasks"]["count"] == 1

    def test_get_hierarchy_status_no_global(self):
        """Test getting hierarchy status when global context doesn't exist"""
        # Setup global context not found
        self.mock_global_repo.get.return_value = None
        self.mock_project_repo.list.return_value = []
        self.mock_branch_repo.list.return_value = []
        self.mock_task_repo.list.return_value = []
        
        status = self.validator.get_hierarchy_status()
        
        assert status["current_state"]["global"]["exists"] is False
        assert status["current_state"]["projects"]["count"] == 0
        assert status["current_state"]["branches"]["count"] == 0
        assert status["current_state"]["tasks"]["count"] == 0

    def test_get_hierarchy_status_with_exceptions(self):
        """Test getting hierarchy status when repositories raise exceptions"""
        # Setup all repos to raise exceptions
        self.mock_global_repo.get.side_effect = Exception("Global repo error")
        self.mock_project_repo.list.side_effect = Exception("Project repo error")
        self.mock_branch_repo.list.side_effect = Exception("Branch repo error")
        self.mock_task_repo.list.side_effect = Exception("Task repo error")
        
        status = self.validator.get_hierarchy_status()
        
        assert status["current_state"]["global"]["exists"] is False
        assert status["current_state"]["projects"]["count"] == 0
        assert status["current_state"]["branches"]["count"] == 0
        assert status["current_state"]["tasks"]["count"] == 0

    def test_context_level_enum_usage(self):
        """Test that ContextLevel enum is used correctly"""
        # Test all context levels are handled
        levels = [ContextLevel.GLOBAL, ContextLevel.PROJECT, ContextLevel.BRANCH, ContextLevel.TASK]
        
        for level in levels:
            # This should not raise an exception for valid levels
            is_valid, error, guidance = self.validator.validate_hierarchy_requirements(level, "test-id", {})
            
            # We expect different results based on level, but no exceptions
            assert isinstance(is_valid, bool)

    @patch('fastmcp.task_management.application.services.context_hierarchy_validator.logger')
    def test_logging_behavior(self, mock_logger):
        """Test that appropriate logging occurs"""
        # Test global context validation logging
        self.mock_global_repo.get.return_value = None
        self.mock_global_repo.list.return_value = [Mock()]
        
        self.validator._validate_project_requirements("project-123")
        
        # Verify debug logging for found global context
        mock_logger.debug.assert_called()

    def test_guidance_structure_completeness(self):
        """Test that guidance structures contain expected fields"""
        # Test project requirements guidance
        self.mock_global_repo.get.return_value = None
        self.mock_global_repo.list.return_value = []
        
        is_valid, error, guidance = self.validator._validate_project_requirements("project-123")
        
        assert guidance is not None
        required_fields = ["error", "explanation", "required_action", "step_by_step"]
        for field in required_fields:
            assert field in guidance

    def test_task_requirements_with_project_hint(self):
        """Test task validation includes project hint when available"""
        task_id = "task-123"
        branch_id = "branch-456"
        project_id = "project-789"
        data = {"branch_id": branch_id, "project_id": project_id}
        
        # Setup branch context doesn't exist
        self.mock_branch_repo.get.return_value = None
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        assert is_valid is False
        # Check that project_id is included in the guidance
        assert "required_actions" in guidance
        branch_create_command = guidance["required_actions"][0]["command"]
        assert project_id in branch_create_command

    def test_find_by_id_with_multiple_parameters(self):
        """Test find_by_id method with multiple parameter scenarios"""
        task_id = "task-123"
        branch_id = "branch-456"
        data = {"branch_id": branch_id}
        
        # Setup branch not found via get
        self.mock_branch_repo.get.return_value = None
        
        # Create a mock find_by_id method that requires multiple parameters
        def mock_find_by_id(session, branch_id):
            return Mock()
        
        mock_find_by_id.__code__ = Mock()
        mock_find_by_id.__code__.co_argcount = 3  # self + 2 parameters
        
        self.mock_branch_repo.find_by_id = mock_find_by_id
        
        is_valid, error, guidance = self.validator._validate_task_requirements(task_id, data)
        
        # Should handle the multi-parameter case gracefully
        assert isinstance(is_valid, bool)