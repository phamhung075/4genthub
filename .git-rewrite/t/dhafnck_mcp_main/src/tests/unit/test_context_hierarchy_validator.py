"""
Unit tests for the Context Hierarchy Validator.

Tests the validation logic and user-friendly error messages for context creation
when parent contexts don't exist in the hierarchy.
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastmcp.task_management.application.services.context_hierarchy_validator import ContextHierarchyValidator
from fastmcp.task_management.domain.value_objects.context_enums import ContextLevel


class TestContextHierarchyValidator:
    
    def setup_method(self, method):
        """Setup method for unit tests - no database operations needed"""
        # Unit tests don't need database cleanup since they use mocks
        pass

    """Test the context hierarchy validator."""
    
    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories."""
        return {
            'global': Mock(),
            'project': Mock(),
            'branch': Mock(),
            'task': Mock()
        }
    
    @pytest.fixture
    def validator(self, mock_repositories):
        """Create a validator instance with mock repositories."""
        return ContextHierarchyValidator(
            global_repo=mock_repositories['global'],
            project_repo=mock_repositories['project'],
            branch_repo=mock_repositories['branch'],
            task_repo=mock_repositories['task']
        )
    
    def test_global_context_always_valid(self, validator):
        """Test that global context creation is always valid (no parent required)."""
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.GLOBAL,
            context_id="global_singleton",
            data={"autonomous_rules": {}}
        )
        
        assert is_valid is True
        assert error_msg is None
        assert guidance is None
    
    def test_project_requires_global_context(self, validator, mock_repositories):
        """Test that project context creation requires global context to exist."""
        # Case 1: Global context doesn't exist
        mock_repositories['global'].get.side_effect = Exception("Not found")
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.PROJECT,
            context_id="proj-123",
            data={"project_name": "Test Project"}
        )
        
        assert is_valid is False
        assert "Global context must be created first" in error_msg
        assert guidance is not None
        assert "command" in guidance
        assert "global_singleton" in guidance["command"]
        assert "explanation" in guidance
        
        # Case 2: Global context exists
        mock_repositories['global'].get.reset_mock()
        mock_repositories['global'].get.side_effect = None  # Remove the exception
        mock_repositories['global'].get.return_value = Mock()
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.PROJECT,
            context_id="proj-123",
            data={"project_name": "Test Project"}
        )
        
        assert is_valid is True
        assert error_msg is None
        assert guidance is None
    
    def test_branch_requires_project_context_and_project_id(self, validator, mock_repositories):
        """Test that branch context creation requires project_id and existing project context."""
        # Case 1: Missing project_id in data
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id="branch-456",
            data={"git_branch_name": "feature/test"}
        )
        
        assert is_valid is False
        assert "Branch context requires project_id" in error_msg
        assert guidance is not None
        assert "required_fields" in guidance
        assert "project_id" in guidance["required_fields"]
        
        # Case 2: project_id provided but project context doesn't exist
        mock_repositories['project'].get.side_effect = Exception("Not found")
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id="branch-456",
            data={"project_id": "proj-123", "git_branch_name": "feature/test"}
        )
        
        assert is_valid is False
        assert "Project context must exist first" in error_msg
        assert guidance is not None
        assert "suggestion" in guidance
        
        # Case 3: Everything exists
        mock_repositories['project'].get.reset_mock()
        mock_repositories['project'].get.side_effect = None
        mock_repositories['project'].get.return_value = Mock()
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id="branch-456",
            data={"project_id": "proj-123", "git_branch_name": "feature/test"}
        )
        
        assert is_valid is True
        assert error_msg is None
        assert guidance is None
    
    def test_task_requires_branch_context_and_branch_id(self, validator, mock_repositories):
        """Test that task context creation requires branch_id and existing branch context."""
        # Case 1: Missing branch_id in data
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"task_data": {"title": "Test Task"}}
        )
        
        assert is_valid is False
        assert "branch_id" in error_msg
        assert guidance is not None
        assert "required_fields" in guidance
        assert "branch_id" in guidance["required_fields"]
        assert "alternative_names" in guidance["required_fields"]
        
        # Case 2: branch_id provided but branch context doesn't exist
        mock_repositories['branch'].get.side_effect = Exception("Not found")
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"branch_id": "branch-456", "task_data": {"title": "Test Task"}}
        )
        
        assert is_valid is False
        assert "Branch context must exist first" in error_msg
        assert guidance is not None
        assert "suggestion" in guidance
        
        # Case 3: Everything exists
        mock_repositories['branch'].get.reset_mock()
        mock_repositories['branch'].get.side_effect = None
        mock_repositories['branch'].get.return_value = Mock()
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"branch_id": "branch-456", "task_data": {"title": "Test Task"}}
        )
        
        assert is_valid is True
        assert error_msg is None
        assert guidance is None
    
    def test_alternative_field_names_for_branch_id(self, validator, mock_repositories):
        """Test that alternative field names work for branch_id."""
        mock_repositories['branch'].get.return_value = Mock()
        
        # Test parent_branch_id
        is_valid, _, _ = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"parent_branch_id": "branch-456", "task_data": {"title": "Test"}}
        )
        assert is_valid is True
        
        # Test git_branch_id
        is_valid, _, _ = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"git_branch_id": "branch-456", "task_data": {"title": "Test"}}
        )
        assert is_valid is True
    
    def test_alternative_field_names_for_project_id(self, validator, mock_repositories):
        """Test that alternative field names work for project_id in branch context."""
        mock_repositories['project'].get.return_value = Mock()
        
        # Test parent_project_id
        is_valid, _, _ = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id="branch-456",
            data={"parent_project_id": "proj-123", "git_branch_name": "test"}
        )
        assert is_valid is True
    
    def test_get_hierarchy_status(self, validator, mock_repositories):
        """Test getting the current hierarchy status."""
        # Setup mock data
        mock_repositories['global'].get.return_value = Mock()
        mock_repositories['project'].list.return_value = [Mock(), Mock()]
        mock_repositories['branch'].list.return_value = [Mock(), Mock(), Mock()]
        mock_repositories['task'].list.return_value = [Mock() for _ in range(5)]
        
        status = validator.get_hierarchy_status()
        
        assert status["hierarchy_levels"] == ["global", "project", "branch", "task"]
        assert status["current_state"]["global"]["exists"] is True
        assert status["current_state"]["projects"]["count"] == 2
        assert status["current_state"]["branches"]["count"] == 3
        assert status["current_state"]["tasks"]["count"] == 5
    
    def test_helpful_error_messages(self, validator, mock_repositories):
        """Test that error messages provide helpful guidance."""
        # Test missing branch_id error
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.TASK,
            context_id="task-789",
            data={"task_data": {"title": "Test"}}
        )
        
        assert not is_valid
        assert "tip" in guidance
        assert "manage_git_branch" in guidance["tip"]
        assert "example" in guidance
        assert "branch_id" in guidance["example"]
        
        # Test missing project context error
        mock_repositories['project'].get.side_effect = Exception("Not found")
        
        is_valid, error_msg, guidance = validator.validate_hierarchy_requirements(
            level=ContextLevel.BRANCH,
            context_id="branch-456",
            data={"project_id": "proj-123"}
        )
        
        assert not is_valid
        assert "suggestion" in guidance
        assert "project context first" in guidance["suggestion"]