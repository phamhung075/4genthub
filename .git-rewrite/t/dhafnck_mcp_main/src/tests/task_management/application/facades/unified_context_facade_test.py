"""Tests for UnifiedContextFacade"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException


class TestUnifiedContextFacade:
    """Test suite for UnifiedContextFacade"""

    @pytest.fixture
    def mock_unified_service(self):
        """Create mock unified context service"""
        service = Mock()
        service.create_context.return_value = {"success": True, "context_id": "test-context"}
        service.get_context.return_value = {"success": True, "data": {"test": "data"}}
        service.update_context.return_value = {"success": True, "updated": True}
        service.delete_context.return_value = {"success": True, "deleted": True}
        service.resolve_context.return_value = {"success": True, "resolved": {"test": "resolved"}}
        service.delegate_context.return_value = {"success": True, "delegated": True}
        service.add_insight.return_value = {"success": True, "insight_added": True}
        service.add_progress.return_value = {"success": True, "progress_added": True}
        service.list_contexts.return_value = {"success": True, "contexts": []}
        service.bootstrap_context_hierarchy.return_value = {"success": True, "bootstrap_completed": True}
        return service

    @pytest.fixture
    def facade(self, mock_unified_service):
        """Create facade instance with mocked service"""
        return UnifiedContextFacade(
            unified_service=mock_unified_service,
            user_id="test-user",
            project_id="test-project",
            git_branch_id="test-branch"
        )

    def test_facade_initialization(self, mock_unified_service):
        """Test facade initializes correctly"""
        user_id = "user-123"
        project_id = "project-456"
        git_branch_id = "branch-789"
        
        facade = UnifiedContextFacade(
            unified_service=mock_unified_service,
            user_id=user_id,
            project_id=project_id,
            git_branch_id=git_branch_id
        )
        
        assert facade._service == mock_unified_service
        assert facade._user_id == user_id
        assert facade._project_id == project_id
        assert facade._git_branch_id == git_branch_id

    def test_facade_initialization_minimal(self, mock_unified_service):
        """Test facade initialization with minimal parameters"""
        facade = UnifiedContextFacade(unified_service=mock_unified_service)
        
        assert facade._service == mock_unified_service
        assert facade._user_id is None
        assert facade._project_id is None
        assert facade._git_branch_id is None

    def test_add_scope_to_data_all_scope(self, facade):
        """Test adding scope information to data"""
        input_data = {"existing": "data"}
        
        result = facade._add_scope_to_data(input_data)
        
        assert result["existing"] == "data"
        assert result["user_id"] == "test-user"
        assert result["project_id"] == "test-project"
        assert result["git_branch_id"] == "test-branch"

    def test_add_scope_to_data_empty_dict(self, facade):
        """Test adding scope to empty dict"""
        result = facade._add_scope_to_data({})
        
        assert result["user_id"] == "test-user"
        assert result["project_id"] == "test-project"
        assert result["git_branch_id"] == "test-branch"

    def test_add_scope_to_data_none_input(self, facade):
        """Test adding scope to None input"""
        result = facade._add_scope_to_data(None)
        
        assert result["user_id"] == "test-user"
        assert result["project_id"] == "test-project"
        assert result["git_branch_id"] == "test-branch"

    def test_add_scope_to_data_existing_scope(self, facade):
        """Test that existing scope data is not overwritten"""
        input_data = {
            "user_id": "existing-user",
            "project_id": "existing-project",
            "git_branch_id": "existing-branch"
        }
        
        result = facade._add_scope_to_data(input_data)
        
        assert result["user_id"] == "existing-user"
        assert result["project_id"] == "existing-project"
        assert result["git_branch_id"] == "existing-branch"

    def test_add_scope_to_data_no_facade_scope(self, mock_unified_service):
        """Test adding scope when facade has no scope information"""
        facade = UnifiedContextFacade(unified_service=mock_unified_service)
        input_data = {"test": "data"}
        
        result = facade._add_scope_to_data(input_data)
        
        assert result == {"test": "data"}
        assert "user_id" not in result
        assert "project_id" not in result
        assert "git_branch_id" not in result

    def test_create_context_success(self, facade, mock_unified_service):
        """Test successful context creation"""
        level = "task"
        context_id = "task-123"
        data = {"title": "Test Task"}
        
        result = facade.create_context(level, context_id, data)
        
        assert result["success"] is True
        mock_unified_service.create_context.assert_called_once()
        
        # Verify call arguments
        call_args = mock_unified_service.create_context.call_args
        assert call_args[0][0] == level  # level
        assert call_args[0][1] == context_id  # context_id
        assert call_args[0][2]["title"] == "Test Task"  # data with scope
        assert call_args[1]["user_id"] == "test-user"
        assert call_args[1]["project_id"] == "test-project"

    def test_create_context_no_data(self, facade, mock_unified_service):
        """Test context creation without data"""
        result = facade.create_context("project", "project-123")
        
        assert result["success"] is True
        mock_unified_service.create_context.assert_called_once()
        
        # Verify scope was added
        call_args = mock_unified_service.create_context.call_args
        data_param = call_args[0][2]
        assert data_param["user_id"] == "test-user"
        assert data_param["project_id"] == "test-project"

    def test_create_context_exception_handling(self, facade, mock_unified_service):
        """Test context creation exception handling"""
        mock_unified_service.create_context.side_effect = ValidationException("Invalid context")
        
        result = facade.create_context("task", "task-123", {"test": "data"})
        
        assert result["success"] is False
        assert "Invalid context" in result["error"]

    def test_run_sync_method(self, facade):
        """Test the _run_sync helper method"""
        test_value = {"test": "result"}
        
        result = facade._run_sync(test_value)
        
        assert result == test_value

    def test_facade_delegation_with_partial_scope(self, mock_unified_service):
        """Test facade with partial scope information"""
        facade = UnifiedContextFacade(
            unified_service=mock_unified_service,
            user_id="test-user",
            project_id=None,  # Missing project_id
            git_branch_id="test-branch"
        )
        
        data = {"test": "data"}
        result_data = facade._add_scope_to_data(data)
        
        assert result_data["user_id"] == "test-user"
        assert result_data["git_branch_id"] == "test-branch"
        assert "project_id" not in result_data

    def test_logging_on_initialization(self, mock_unified_service):
        """Test that initialization is logged"""
        with patch('fastmcp.task_management.application.facades.unified_context_facade.logger') as mock_logger:
            facade = UnifiedContextFacade(
                unified_service=mock_unified_service,
                user_id="test-user",
                project_id="test-project",
                git_branch_id="test-branch"
            )
            
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert "UnifiedContextFacade initialized" in log_call
            assert "user=test-user" in log_call
            assert "project=test-project" in log_call
            assert "branch=test-branch" in log_call

    def test_facade_service_delegation(self, facade, mock_unified_service):
        """Test that facade properly delegates to service"""
        # Test that facade has direct access to service
        assert facade._service == mock_unified_service
        
        # Any method that would be called should delegate to the service
        facade.create_context("task", "task-123")
        mock_unified_service.create_context.assert_called_once()

    def test_create_context_data_modification(self, facade, mock_unified_service):
        """Test that create_context properly modifies data with scope"""
        original_data = {"original": "value"}
        
        facade.create_context("task", "task-123", original_data)
        
        # Verify original data is not modified
        assert original_data == {"original": "value"}
        
        # Verify service received data with scope
        call_args = mock_unified_service.create_context.call_args
        modified_data = call_args[0][2]
        assert modified_data["original"] == "value"
        assert modified_data["user_id"] == "test-user"
        assert modified_data["project_id"] == "test-project"
        assert modified_data["git_branch_id"] == "test-branch"

    def test_facade_error_handling_general_exception(self, facade, mock_unified_service):
        """Test general exception handling in facade"""
        mock_unified_service.create_context.side_effect = RuntimeError("Unexpected error")
        
        result = facade.create_context("task", "task-123")
        
        assert result["success"] is False
        assert "error" in result
        # Should handle any exception, not just ValidationException

    def test_facade_method_parameters(self, facade, mock_unified_service):
        """Test that facade methods accept expected parameters"""
        import inspect
        
        # Check create_context signature
        sig = inspect.signature(facade.create_context)
        params = list(sig.parameters.keys())
        
        assert 'level' in params
        assert 'context_id' in params
        assert 'data' in params
        
        # Verify optional parameter
        assert sig.parameters['data'].default is None

    def test_facade_with_different_service_responses(self, facade, mock_unified_service):
        """Test facade handles different service response formats"""
        # Test with different success response
        mock_unified_service.create_context.return_value = {
            "success": True,
            "context": {"id": "ctx-123", "data": {"test": "data"}},
            "metadata": {"created_at": "2025-01-01"}
        }
        
        result = facade.create_context("task", "task-123")
        
        assert result["success"] is True
        assert "context" in result
        assert "metadata" in result

    def test_scope_information_priority(self, facade):
        """Test that explicit data takes priority over facade scope"""
        data_with_explicit_user = {
            "user_id": "explicit-user",
            "other_data": "value"
        }
        
        result = facade._add_scope_to_data(data_with_explicit_user)
        
        # Explicit user_id should be preserved
        assert result["user_id"] == "explicit-user"
        # But facade scope should still be added where missing
        assert result["project_id"] == "test-project"
        assert result["git_branch_id"] == "test-branch"
        assert result["other_data"] == "value"

    def test_get_context_success(self, facade, mock_unified_service):
        """Test successful get_context operation"""
        mock_unified_service.get_context.return_value = {
            "success": True,
            "context": {"test": "data", "level": "task"}
        }
        
        result = facade.get_context(
            level="task",
            context_id="task-123",
            include_inherited=True,
            force_refresh=False,
            user_id="specific-user"
        )
        
        assert result["success"] is True
        assert "context" in result
        mock_unified_service.get_context.assert_called_once_with(
            "task", "task-123", True, False, "specific-user"
        )

    def test_get_context_exception(self, facade, mock_unified_service):
        """Test get_context exception handling"""
        mock_unified_service.get_context.side_effect = RuntimeError("Service error")
        
        result = facade.get_context("task", "task-123")
        
        assert result["success"] is False
        assert "Service error" in result["error"]

    def test_get_context_summary_with_context(self, facade, mock_unified_service):
        """Test get_context_summary when context exists"""
        mock_unified_service.get_context.return_value = {
            "success": True,
            "context": {
                "test_data": "some value",
                "updated_at": "2025-01-27T12:00:00Z"
            }
        }
        
        result = facade.get_context_summary("task-123")
        
        assert result["success"] is True
        assert result["has_context"] is True
        assert result["context_size"] > 0
        assert result["last_updated"] == "2025-01-27T12:00:00Z"
        
        # Verify it called with correct parameters
        mock_unified_service.get_context.assert_called_once_with(
            level="task",
            context_id="task-123",
            include_inherited=False,
            force_refresh=False
        )

    def test_get_context_summary_without_context(self, facade, mock_unified_service):
        """Test get_context_summary when context doesn't exist"""
        mock_unified_service.get_context.return_value = {
            "success": False
        }
        
        result = facade.get_context_summary("task-123")
        
        assert result["success"] is True
        assert result["has_context"] is False
        assert result["context_size"] == 0
        assert result["last_updated"] is None

    def test_get_context_summary_exception(self, facade, mock_unified_service):
        """Test get_context_summary exception handling"""
        mock_unified_service.get_context.side_effect = RuntimeError("Service error")
        
        result = facade.get_context_summary("task-123")
        
        assert result["success"] is False
        assert result["has_context"] is False
        assert "Service error" in result["error"]

    def test_update_context_success(self, facade, mock_unified_service):
        """Test successful update_context operation"""
        update_data = {"status": "completed"}
        
        result = facade.update_context("task", "task-123", update_data)
        
        assert result["success"] is True
        assert result["updated"] is True
        
        # Verify call and that scope was added
        call_args = mock_unified_service.update_context.call_args
        assert call_args[0][0] == "task"
        assert call_args[0][1] == "task-123"
        assert call_args[0][2]["status"] == "completed"
        assert call_args[0][2]["user_id"] == "test-user"
        assert call_args[0][3] is True  # propagate_changes default

    def test_update_context_no_propagation(self, facade, mock_unified_service):
        """Test update_context with propagation disabled"""
        result = facade.update_context(
            "task", "task-123", {"data": "test"}, propagate_changes=False
        )
        
        assert result["success"] is True
        call_args = mock_unified_service.update_context.call_args
        assert call_args[0][3] is False  # propagate_changes

    def test_delete_context_success(self, facade, mock_unified_service):
        """Test successful delete_context operation"""
        result = facade.delete_context("task", "task-123")
        
        assert result["success"] is True
        assert result["deleted"] is True
        mock_unified_service.delete_context.assert_called_once_with("task", "task-123")

    def test_delete_context_exception(self, facade, mock_unified_service):
        """Test delete_context exception handling"""
        mock_unified_service.delete_context.side_effect = ValidationException("Cannot delete")
        
        result = facade.delete_context("task", "task-123")
        
        assert result["success"] is False
        assert "Cannot delete" in result["error"]

    def test_resolve_context_success(self, facade, mock_unified_service):
        """Test successful resolve_context operation"""
        result = facade.resolve_context("task", "task-123", force_refresh=True)
        
        assert result["success"] is True
        assert result["resolved"]["test"] == "resolved"
        mock_unified_service.resolve_context.assert_called_once_with(
            "task", "task-123", True
        )

    def test_delegate_context_success(self, facade, mock_unified_service):
        """Test successful delegate_context operation"""
        delegate_data = {"pattern": "reusable_auth"}
        
        result = facade.delegate_context(
            "task", "task-123", "project", delegate_data, "Reusable auth pattern"
        )
        
        assert result["success"] is True
        assert result["delegated"] is True
        mock_unified_service.delegate_context.assert_called_once_with(
            "task", "task-123", "project", delegate_data, "Reusable auth pattern"
        )

    def test_add_insight_success(self, facade, mock_unified_service):
        """Test successful add_insight operation"""
        result = facade.add_insight(
            "task", "task-123", "Found optimization opportunity",
            category="performance", importance="high", agent="test-agent"
        )
        
        assert result["success"] is True
        assert result["insight_added"] is True
        mock_unified_service.add_insight.assert_called_once_with(
            "task", "task-123", "Found optimization opportunity",
            "performance", "high", "test-agent"
        )

    def test_add_progress_success(self, facade, mock_unified_service):
        """Test successful add_progress operation"""
        result = facade.add_progress(
            "task", "task-123", "Completed initial setup", agent="test-agent"
        )
        
        assert result["success"] is True
        assert result["progress_added"] is True
        mock_unified_service.add_progress.assert_called_once_with(
            "task", "task-123", "Completed initial setup", "test-agent"
        )

    def test_list_contexts_with_filters(self, facade, mock_unified_service):
        """Test list_contexts with custom filters"""
        custom_filters = {"status": "active"}
        
        result = facade.list_contexts("task", filters=custom_filters)
        
        assert result["success"] is True
        
        # Verify filters were enhanced with scope
        call_args = mock_unified_service.list_contexts.call_args
        filters_used = call_args[0][1]
        assert filters_used["status"] == "active"
        assert filters_used["user_id"] == "test-user"
        assert filters_used["project_id"] == "test-project"
        assert filters_used["git_branch_id"] == "test-branch"

    def test_list_contexts_project_level(self, facade, mock_unified_service):
        """Test list_contexts at project level doesn't filter by project_id"""
        result = facade.list_contexts("project")
        
        assert result["success"] is True
        
        # Verify project level doesn't include project_id filter
        call_args = mock_unified_service.list_contexts.call_args
        filters_used = call_args[0][1]
        assert filters_used["user_id"] == "test-user"
        assert "project_id" not in filters_used
        assert "git_branch_id" not in filters_used

    def test_list_contexts_branch_level(self, facade, mock_unified_service):
        """Test list_contexts at branch level doesn't filter by git_branch_id"""
        result = facade.list_contexts("branch")
        
        assert result["success"] is True
        
        # Verify branch level includes project but not git_branch_id filter
        call_args = mock_unified_service.list_contexts.call_args
        filters_used = call_args[0][1]
        assert filters_used["user_id"] == "test-user"
        assert filters_used["project_id"] == "test-project"
        assert "git_branch_id" not in filters_used

    def test_bootstrap_context_hierarchy_success(self, facade, mock_unified_service):
        """Test successful bootstrap_context_hierarchy operation"""
        result = facade.bootstrap_context_hierarchy()
        
        assert result["success"] is True
        assert result["bootstrap_completed"] is True
        
        # Verify it used facade scope
        mock_unified_service.bootstrap_context_hierarchy.assert_called_once_with(
            user_id="test-user",
            project_id="test-project",
            branch_id="test-branch"
        )

    def test_bootstrap_context_hierarchy_with_overrides(self, facade, mock_unified_service):
        """Test bootstrap_context_hierarchy with parameter overrides"""
        result = facade.bootstrap_context_hierarchy(
            project_id="override-project",
            branch_id="override-branch"
        )
        
        assert result["success"] is True
        
        # Verify it used override values
        mock_unified_service.bootstrap_context_hierarchy.assert_called_once_with(
            user_id="test-user",
            project_id="override-project",
            branch_id="override-branch"
        )

    def test_bootstrap_context_hierarchy_exception(self, facade, mock_unified_service):
        """Test bootstrap_context_hierarchy exception handling"""
        mock_unified_service.bootstrap_context_hierarchy.side_effect = RuntimeError("Bootstrap failed")
        
        result = facade.bootstrap_context_hierarchy()
        
        assert result["success"] is False
        assert result["bootstrap_completed"] is False
        assert "Bootstrap failed" in result["error"]

    def test_create_context_flexible_with_auto_create(self, facade, mock_unified_service):
        """Test create_context_flexible with auto-create enabled"""
        data = {"test": "data"}
        
        result = facade.create_context_flexible(
            "task", "task-123", data, auto_create_parents=True
        )
        
        assert result["success"] is True
        
        # Verify service call
        call_kwargs = mock_unified_service.create_context.call_args[1]
        assert call_kwargs["level"] == "task"
        assert call_kwargs["context_id"] == "task-123"
        assert call_kwargs["auto_create_parents"] is True
        assert "allow_orphaned_creation" not in call_kwargs["data"]

    def test_create_context_flexible_without_auto_create(self, facade, mock_unified_service):
        """Test create_context_flexible with auto-create disabled"""
        result = facade.create_context_flexible(
            "task", "task-123", auto_create_parents=False
        )
        
        assert result["success"] is True
        
        # Verify service call and special flag
        call_kwargs = mock_unified_service.create_context.call_args[1]
        assert call_kwargs["auto_create_parents"] is False
        assert call_kwargs["data"]["allow_orphaned_creation"] is True

    def test_create_context_flexible_exception(self, facade, mock_unified_service):
        """Test create_context_flexible exception handling"""
        mock_unified_service.create_context.side_effect = ValidationException("Invalid creation")
        
        result = facade.create_context_flexible("task", "task-123")
        
        assert result["success"] is False
        assert "Invalid creation" in result["error"]