"""
Tests for UnifiedContextFacade - Comprehensive facade testing
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastmcp.task_management.application.facades.unified_context_facade import UnifiedContextFacade
from fastmcp.task_management.application.services.unified_context_service import UnifiedContextService
from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException


class TestUnifiedContextFacade:
    """Test cases for UnifiedContextFacade"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock unified context service"""
        return Mock(spec=UnifiedContextService)
    
    @pytest.fixture
    def facade(self, mock_service):
        """Create facade instance for testing"""
        return UnifiedContextFacade(
            unified_service=mock_service,
            user_id="test-user-123",
            project_id="test-project-456",
            git_branch_id="test-branch-789"
        )
    
    @pytest.fixture
    def minimal_facade(self, mock_service):
        """Create facade with minimal scope"""
        return UnifiedContextFacade(unified_service=mock_service)
    
    def test_facade_initialization_with_full_scope(self, mock_service):
        """Test facade initialization with all scope parameters"""
        facade = UnifiedContextFacade(
            unified_service=mock_service,
            user_id="user123",
            project_id="proj456", 
            git_branch_id="branch789"
        )
        
        assert facade._service == mock_service
        assert facade._user_id == "user123"
        assert facade._project_id == "proj456"
        assert facade._git_branch_id == "branch789"
    
    def test_facade_initialization_minimal_scope(self, mock_service):
        """Test facade initialization with minimal parameters"""
        facade = UnifiedContextFacade(unified_service=mock_service)
        
        assert facade._service == mock_service
        assert facade._user_id is None
        assert facade._project_id is None
        assert facade._git_branch_id is None
    
    def test_add_scope_to_data_with_all_scope(self, facade):
        """Test adding scope information to data"""
        data = {"existing_key": "value"}
        
        result = facade._add_scope_to_data(data)
        
        expected = {
            "existing_key": "value",
            "user_id": "test-user-123",
            "project_id": "test-project-456",
            "git_branch_id": "test-branch-789"
        }
        assert result == expected
    
    def test_add_scope_to_data_preserves_existing(self, facade):
        """Test that existing scope data is not overridden"""
        data = {
            "user_id": "existing-user",
            "project_id": "existing-project",
            "custom_field": "value"
        }
        
        result = facade._add_scope_to_data(data)
        
        assert result["user_id"] == "existing-user"
        assert result["project_id"] == "existing-project"
        assert result["git_branch_id"] == "test-branch-789"  # Added
        assert result["custom_field"] == "value"
    
    def test_add_scope_to_data_empty_input(self, facade):
        """Test adding scope to empty/None data"""
        result = facade._add_scope_to_data(None)
        
        expected = {
            "user_id": "test-user-123",
            "project_id": "test-project-456",
            "git_branch_id": "test-branch-789"
        }
        assert result == expected
    
    def test_add_scope_to_data_minimal_scope(self, minimal_facade):
        """Test adding scope with minimal facade scope"""
        data = {"key": "value"}
        
        result = minimal_facade._add_scope_to_data(data)
        
        assert result == {"key": "value"}  # No scope added
    
    def test_create_context_success(self, facade, mock_service):
        """Test successful context creation"""
        mock_service.create_context.return_value = {
            "success": True,
            "context_id": "task-123",
            "data": {"created": True}
        }
        
        result = facade.create_context(
            level="task",
            context_id="task-123",
            data={"title": "Test Task"}
        )
        
        assert result["success"] is True
        assert result["context_id"] == "task-123"
        
        # Verify service was called with scoped data using keyword arguments
        mock_service.create_context.assert_called_once()
        call_kwargs = mock_service.create_context.call_args.kwargs
        assert call_kwargs["level"] == "task"
        assert call_kwargs["context_id"] == "task-123"
        assert "user_id" in call_kwargs["data"]
        assert "project_id" in call_kwargs["data"]
        assert "git_branch_id" in call_kwargs["data"]
        assert call_kwargs["user_id"] == "test-user-123"
        assert call_kwargs["project_id"] == "test-project-456"
    
    def test_create_context_with_none_data(self, facade, mock_service):
        """Test context creation with None data"""
        mock_service.create_context.return_value = {"success": True}
        
        facade.create_context(level="project", context_id="proj-123", data=None)
        
        # Verify scope was still added even with None data using keyword arguments
        call_kwargs = mock_service.create_context.call_args.kwargs
        assert "user_id" in call_kwargs["data"]
        assert "project_id" in call_kwargs["data"]
    
    def test_create_context_service_exception(self, facade, mock_service):
        """Test context creation when service raises exception"""
        mock_service.create_context.side_effect = ValidationException("Test error")
        
        result = facade.create_context(level="task", context_id="task-123")
        
        assert result["success"] is False
        assert "Test error" in result["error"]
    
    def test_get_context_success(self, facade, mock_service):
        """Test successful context retrieval"""
        mock_service.get_context.return_value = {
            "success": True,
            "context": {"data": "test"},
            "inherited": True
        }
        
        result = facade.get_context(
            level="task",
            context_id="task-123",
            include_inherited=True,
            force_refresh=True
        )
        
        assert result["success"] is True
        assert result["context"]["data"] == "test"
        
        mock_service.get_context.assert_called_once_with(
            "task", "task-123", True, True, None
        )
    
    def test_get_context_default_parameters(self, facade, mock_service):
        """Test get_context with default parameters"""
        mock_service.get_context.return_value = {"success": True}
        
        facade.get_context(level="branch", context_id="branch-456")
        
        mock_service.get_context.assert_called_once_with(
            "branch", "branch-456", False, False, None
        )
    
    def test_get_context_service_exception(self, facade, mock_service):
        """Test get_context when service raises exception"""
        mock_service.get_context.side_effect = Exception("Service error")
        
        result = facade.get_context(level="task", context_id="task-123")
        
        assert result["success"] is False
        assert "Service error" in result["error"]
    
    def test_update_context_success(self, facade, mock_service):
        """Test successful context update"""
        mock_service.update_context.return_value = {
            "success": True,
            "updated": True
        }
        
        update_data = {"status": "completed"}
        result = facade.update_context(
            level="task",
            context_id="task-123",
            data=update_data,
            propagate_changes=False
        )
        
        assert result["success"] is True
        assert result["updated"] is True
        
        # Verify scoped data was passed to service
        call_args = mock_service.update_context.call_args
        assert call_args[0][0] == "task"
        assert call_args[0][1] == "task-123"
        assert "user_id" in call_args[0][2]
        assert "status" in call_args[0][2]
        assert call_args[0][3] is False  # propagate_changes
    
    def test_update_context_default_propagate(self, facade, mock_service):
        """Test update_context with default propagate_changes"""
        mock_service.update_context.return_value = {"success": True}
        
        facade.update_context(
            level="project",
            context_id="proj-123",
            data={"key": "value"}
        )
        
        call_args = mock_service.update_context.call_args
        assert call_args[0][3] is True  # Default propagate_changes=True
    
    def test_update_context_service_exception(self, facade, mock_service):
        """Test update_context when service raises exception"""
        mock_service.update_context.side_effect = Exception("Update failed")
        
        result = facade.update_context(
            level="task",
            context_id="task-123",
            data={"key": "value"}
        )
        
        assert result["success"] is False
        assert "Update failed" in result["error"]
    
    def test_delete_context_success(self, facade, mock_service):
        """Test successful context deletion"""
        mock_service.delete_context.return_value = {
            "success": True,
            "deleted": True
        }
        
        result = facade.delete_context(level="task", context_id="task-123")
        
        assert result["success"] is True
        assert result["deleted"] is True
        
        mock_service.delete_context.assert_called_once_with("task", "task-123")
    
    def test_delete_context_service_exception(self, facade, mock_service):
        """Test delete_context when service raises exception"""
        mock_service.delete_context.side_effect = Exception("Delete failed")
        
        result = facade.delete_context(level="task", context_id="task-123")
        
        assert result["success"] is False
        assert "Delete failed" in result["error"]
    
    def test_resolve_context_success(self, facade, mock_service):
        """Test successful context resolution with inheritance"""
        mock_service.resolve_context.return_value = {
            "success": True,
            "resolved_context": {"full": "data"},
            "inheritance_chain": ["global", "project", "branch", "task"]
        }
        
        result = facade.resolve_context(
            level="task",
            context_id="task-123",
            force_refresh=True
        )
        
        assert result["success"] is True
        assert "inheritance_chain" in result
        
        mock_service.resolve_context.assert_called_once_with(
            "task", "task-123", True
        )
    
    def test_resolve_context_default_refresh(self, facade, mock_service):
        """Test resolve_context with default force_refresh"""
        mock_service.resolve_context.return_value = {"success": True}
        
        facade.resolve_context(level="branch", context_id="branch-456")
        
        mock_service.resolve_context.assert_called_once_with(
            "branch", "branch-456", False
        )
    
    def test_resolve_context_service_exception(self, facade, mock_service):
        """Test resolve_context when service raises exception"""
        mock_service.resolve_context.side_effect = Exception("Resolve failed")
        
        result = facade.resolve_context(level="task", context_id="task-123")
        
        assert result["success"] is False
        assert "Resolve failed" in result["error"]
    
    def test_delegate_context_success(self, facade, mock_service):
        """Test successful context delegation"""
        mock_service.delegate_context.return_value = {
            "success": True,
            "delegated": True,
            "target_level": "project"
        }
        
        delegate_data = {"pattern": "reusable_component"}
        result = facade.delegate_context(
            level="task",
            context_id="task-123",
            delegate_to="project",
            data=delegate_data,
            delegation_reason="Reusable across tasks"
        )
        
        assert result["success"] is True
        assert result["delegated"] is True
        
        mock_service.delegate_context.assert_called_once_with(
            "task", "task-123", "project", delegate_data, "Reusable across tasks"
        )
    
    def test_delegate_context_no_reason(self, facade, mock_service):
        """Test delegate_context without delegation reason"""
        mock_service.delegate_context.return_value = {"success": True}
        
        facade.delegate_context(
            level="branch",
            context_id="branch-456",
            delegate_to="project",
            data={"pattern": "test"}
        )
        
        call_args = mock_service.delegate_context.call_args
        assert call_args[0][4] is None  # delegation_reason
    
    def test_delegate_context_service_exception(self, facade, mock_service):
        """Test delegate_context when service raises exception"""
        mock_service.delegate_context.side_effect = Exception("Delegation failed")
        
        result = facade.delegate_context(
            level="task",
            context_id="task-123",
            delegate_to="project",
            data={"key": "value"}
        )
        
        assert result["success"] is False
        assert "Delegation failed" in result["error"]
    
    def test_add_insight_success(self, facade, mock_service):
        """Test successful insight addition"""
        mock_service.add_insight.return_value = {
            "success": True,
            "insight_added": True
        }
        
        result = facade.add_insight(
            level="task",
            context_id="task-123",
            content="Important discovery",
            category="technical",
            importance="high",
            agent="test-agent"
        )
        
        assert result["success"] is True
        assert result["insight_added"] is True
        
        mock_service.add_insight.assert_called_once_with(
            "task", "task-123", "Important discovery", "technical", "high", "test-agent"
        )
    
    def test_add_insight_minimal_params(self, facade, mock_service):
        """Test add_insight with minimal parameters"""
        mock_service.add_insight.return_value = {"success": True}
        
        facade.add_insight(
            level="project",
            context_id="proj-456",
            content="Basic insight"
        )
        
        call_args = mock_service.add_insight.call_args
        assert call_args[0][2] == "Basic insight"
        assert call_args[0][3] is None  # category
        assert call_args[0][4] is None  # importance
        assert call_args[0][5] is None  # agent
    
    def test_add_insight_service_exception(self, facade, mock_service):
        """Test add_insight when service raises exception"""
        mock_service.add_insight.side_effect = Exception("Insight failed")
        
        result = facade.add_insight(
            level="task",
            context_id="task-123",
            content="Test insight"
        )
        
        assert result["success"] is False
        assert "Insight failed" in result["error"]
    
    def test_add_progress_success(self, facade, mock_service):
        """Test successful progress addition"""
        mock_service.add_progress.return_value = {
            "success": True,
            "progress_added": True
        }
        
        result = facade.add_progress(
            level="task",
            context_id="task-123",
            content="50% complete",
            agent="progress-agent"
        )
        
        assert result["success"] is True
        assert result["progress_added"] is True
        
        mock_service.add_progress.assert_called_once_with(
            "task", "task-123", "50% complete", "progress-agent"
        )
    
    def test_add_progress_no_agent(self, facade, mock_service):
        """Test add_progress without agent"""
        mock_service.add_progress.return_value = {"success": True}
        
        facade.add_progress(
            level="branch",
            context_id="branch-789",
            content="Progress update"
        )
        
        call_args = mock_service.add_progress.call_args
        assert call_args[0][3] is None  # agent
    
    def test_add_progress_service_exception(self, facade, mock_service):
        """Test add_progress when service raises exception"""
        mock_service.add_progress.side_effect = Exception("Progress failed")
        
        result = facade.add_progress(
            level="task",
            context_id="task-123",
            content="Progress update"
        )
        
        assert result["success"] is False
        assert "Progress failed" in result["error"]
    
    def test_list_contexts_success(self, facade, mock_service):
        """Test successful context listing"""
        mock_service.list_contexts.return_value = {
            "success": True,
            "contexts": [{"id": "ctx1"}, {"id": "ctx2"}],
            "count": 2
        }
        
        result = facade.list_contexts(
            level="task",
            filters={"status": "active"}
        )
        
        assert result["success"] is True
        assert result["count"] == 2
        
        # Verify filters included scope
        call_args = mock_service.list_contexts.call_args
        filters = call_args[0][1]
        assert filters["status"] == "active"
        assert filters["user_id"] == "test-user-123"
        assert filters["project_id"] == "test-project-456"
        assert filters["git_branch_id"] == "test-branch-789"
    
    def test_list_contexts_no_filters(self, facade, mock_service):
        """Test list_contexts without initial filters"""
        mock_service.list_contexts.return_value = {"success": True}
        
        facade.list_contexts(level="project")
        
        call_args = mock_service.list_contexts.call_args
        filters = call_args[0][1]
        assert "user_id" in filters
        # When listing projects, we don't filter by project_id or git_branch_id
        assert "project_id" not in filters
        assert "git_branch_id" not in filters
    
    def test_list_contexts_minimal_scope(self, minimal_facade, mock_service):
        """Test list_contexts with minimal facade scope"""
        mock_service.list_contexts.return_value = {"success": True}
        
        minimal_facade.list_contexts(
            level="global",
            filters={"custom": "filter"}
        )
        
        call_args = mock_service.list_contexts.call_args
        filters = call_args[0][1]
        assert filters == {"custom": "filter"}  # No scope added
    
    def test_list_contexts_service_exception(self, facade, mock_service):
        """Test list_contexts when service raises exception"""
        mock_service.list_contexts.side_effect = Exception("List failed")
        
        result = facade.list_contexts(level="task")
        
        assert result["success"] is False
        assert "List failed" in result["error"]
    
    def test_all_methods_handle_exceptions_gracefully(self, facade, mock_service):
        """Test that all methods handle exceptions gracefully"""
        # Configure all service methods to raise exceptions
        exception_methods = [
            'create_context', 'get_context', 'update_context', 'delete_context',
            'resolve_context', 'delegate_context', 'add_insight', 'add_progress',
            'list_contexts'
        ]
        
        for method_name in exception_methods:
            setattr(mock_service, method_name, Mock(side_effect=Exception("Test error")))
        
        # Test each facade method returns error response
        methods_to_test = [
            lambda: facade.create_context("task", "id"),
            lambda: facade.get_context("task", "id"),
            lambda: facade.update_context("task", "id", {}),
            lambda: facade.delete_context("task", "id"),
            lambda: facade.resolve_context("task", "id"),
            lambda: facade.delegate_context("task", "id", "project", {}),
            lambda: facade.add_insight("task", "id", "content"),
            lambda: facade.add_progress("task", "id", "content"),
            lambda: facade.list_contexts("task")
        ]
        
        for method in methods_to_test:
            result = method()
            assert result["success"] is False
            assert "error" in result
    
    def test_logging_initialization(self, mock_service):
        """Test that facade logs initialization properly"""
        with patch('fastmcp.task_management.application.facades.unified_context_facade.logger') as mock_logger:
            UnifiedContextFacade(
                unified_service=mock_service,
                user_id="user123",
                project_id="proj456",
                git_branch_id="branch789"
            )
            
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "UnifiedContextFacade initialized" in log_msg
            assert "user=user123" in log_msg
            assert "project=proj456" in log_msg
            assert "branch=branch789" in log_msg


class TestUnifiedContextFacadeIntegration:
    """Integration-style tests for UnifiedContextFacade"""
    
    def test_create_and_get_context_flow(self):
        """Test typical create then get context flow"""
        mock_service = Mock(spec=UnifiedContextService)
        facade = UnifiedContextFacade(
            unified_service=mock_service,
            project_id="test-project"
        )
        
        # Configure service responses
        mock_service.create_context.return_value = {
            "success": True,
            "context_id": "task-123"
        }
        mock_service.get_context.return_value = {
            "success": True,
            "context": {"title": "Test Task"}
        }
        
        # Create context
        create_result = facade.create_context(
            level="task",
            context_id="task-123",
            data={"title": "Test Task"}
        )
        
        # Get context
        get_result = facade.get_context(
            level="task",
            context_id="task-123",
            include_inherited=True
        )
        
        assert create_result["success"] is True
        assert get_result["success"] is True
        assert mock_service.create_context.called
        assert mock_service.get_context.called
    
    def test_update_with_propagation_flow(self):
        """Test update context with propagation flow"""
        mock_service = Mock(spec=UnifiedContextService)
        facade = UnifiedContextFacade(
            unified_service=mock_service,
            project_id="test-project",
            git_branch_id="test-branch"
        )
        
        mock_service.update_context.return_value = {
            "success": True,
            "propagated_to": ["child1", "child2"]
        }
        
        result = facade.update_context(
            level="branch",
            context_id="test-branch",
            data={"status": "completed"},
            propagate_changes=True
        )
        
        assert result["success"] is True
        
        # Verify propagation was enabled
        call_args = mock_service.update_context.call_args
        assert call_args[0][3] is True  # propagate_changes