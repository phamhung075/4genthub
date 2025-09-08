"""
Tests for Progress Operation Factory

Tests the factory class that coordinates progress operations by routing them to appropriate handlers.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory import (
    ProgressOperationFactory
)
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ErrorCodes


@pytest.fixture
def mock_response_formatter():
    """Create mock response formatter."""
    formatter = Mock(spec=StandardResponseFormatter)
    formatter.create_error_response.return_value = {"success": False, "error": "Test error"}
    formatter.create_success_response.return_value = {"success": True, "data": {}}
    return formatter


@pytest.fixture
def mock_task_facade():
    """Create mock task application facade."""
    facade = Mock()
    facade.get_task.return_value = {"success": True, "task": {"id": "task123", "status": "in_progress"}}
    facade.update_task.return_value = {"success": True, "task": {"id": "task123", "status": "updated"}}
    return facade


@pytest.fixture
def mock_context_facade_factory():
    """Create mock unified context facade factory."""
    factory = Mock()
    mock_facade = Mock()
    mock_facade.manage_context.return_value = {"success": True, "context": {}}
    factory.create_unified_facade.return_value = mock_facade
    return factory


@pytest.fixture
def mock_progress_handler():
    """Create mock progress reporting handler."""
    handler = Mock()
    handler.report_progress.return_value = {"success": True, "progress": {}}
    handler.quick_task_update.return_value = {"success": True, "task": {}}
    return handler


@pytest.fixture
def mock_workflow_handler():
    """Create mock workflow handler."""
    handler = Mock()
    handler.checkpoint_work.return_value = {"success": True, "checkpoint": {}}
    return handler


@pytest.fixture
def mock_context_handler():
    """Create mock context handler."""
    handler = Mock()
    handler.update_work_context.return_value = {"success": True, "context": {}}
    return handler


@pytest.fixture
def operation_factory(mock_response_formatter, mock_task_facade, mock_context_facade_factory):
    """Create ProgressOperationFactory instance with mocked dependencies."""
    with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ProgressReportingHandler') as mock_progress, \
         patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.WorkflowHandler') as mock_workflow, \
         patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ContextHandler') as mock_context:
        
        factory = ProgressOperationFactory(
            response_formatter=mock_response_formatter,
            task_facade=mock_task_facade,
            context_facade_factory=mock_context_facade_factory
        )
        
        # Inject mocked handlers
        factory._progress_handler = Mock()
        factory._workflow_handler = Mock()
        factory._context_handler = Mock()
        
        return factory


class TestProgressOperationFactory:
    """Test suite for ProgressOperationFactory."""

    def test_factory_initialization(self, mock_response_formatter, mock_task_facade, mock_context_facade_factory):
        """Test factory initialization with dependencies."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ProgressReportingHandler'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.WorkflowHandler'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ContextHandler'):
            
            factory = ProgressOperationFactory(
                response_formatter=mock_response_formatter,
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            assert factory._response_formatter == mock_response_formatter
            assert factory._task_facade == mock_task_facade
            assert factory._context_facade_factory == mock_context_facade_factory
            assert hasattr(factory, '_progress_handler')
            assert hasattr(factory, '_workflow_handler')
            assert hasattr(factory, '_context_handler')


class TestReportProgressOperation:
    """Test report progress operation."""

    def test_report_progress_success(self, operation_factory):
        """Test successful progress reporting."""
        # Mock handler response
        expected_response = {
            "success": True,
            "progress": {
                "task_id": "task123",
                "percentage": 50,
                "description": "Halfway done"
            }
        }
        operation_factory._progress_handler.report_progress.return_value = expected_response
        
        result = operation_factory.handle_operation(
            "report_progress",
            task_id="task123",
            progress_type="implementation",
            description="Halfway done",
            percentage=50,
            files_affected=["file1.py", "file2.py"],
            next_steps=["Complete testing"]
        )
        
        assert result == expected_response
        operation_factory._progress_handler.report_progress.assert_called_once_with(
            task_id="task123",
            progress_type="implementation",
            description="Halfway done",
            percentage=50,
            files_affected=["file1.py", "file2.py"],
            next_steps=["Complete testing"]
        )
    
    def test_report_progress_with_minimal_params(self, operation_factory):
        """Test progress reporting with minimal parameters."""
        operation_factory._progress_handler.report_progress.return_value = {"success": True}
        
        result = operation_factory.handle_operation(
            "report_progress",
            task_id="task123",
            description="Progress update"
        )
        
        assert result["success"] is True
        operation_factory._progress_handler.report_progress.assert_called_once_with(
            task_id="task123",
            progress_type=None,
            description="Progress update",
            percentage=None,
            files_affected=None,
            next_steps=None
        )


class TestQuickTaskUpdateOperation:
    """Test quick task update operation."""

    def test_quick_task_update_success(self, operation_factory):
        """Test successful quick task update."""
        expected_response = {
            "success": True,
            "task": {
                "id": "task123",
                "status": "in_progress",
                "notes": "Updated notes"
            }
        }
        operation_factory._progress_handler.quick_task_update.return_value = expected_response
        
        result = operation_factory.handle_operation(
            "quick_task_update",
            task_id="task123",
            status="in_progress",
            notes="Working on implementation",
            completed_work=["Implemented feature X"]
        )
        
        assert result == expected_response
        operation_factory._progress_handler.quick_task_update.assert_called_once_with(
            task_id="task123",
            status="in_progress",
            notes="Working on implementation",
            completed_work=["Implemented feature X"]
        )
    
    def test_quick_task_update_status_only(self, operation_factory):
        """Test quick update with status only."""
        operation_factory._progress_handler.quick_task_update.return_value = {"success": True}
        
        result = operation_factory.handle_operation(
            "quick_task_update",
            task_id="task123",
            status="completed"
        )
        
        assert result["success"] is True
        operation_factory._progress_handler.quick_task_update.assert_called_once_with(
            task_id="task123",
            status="completed",
            notes=None,
            completed_work=None
        )


class TestWorkflowOperations:
    """Test workflow operations."""

    def test_checkpoint_work_success(self, operation_factory):
        """Test successful work checkpoint."""
        expected_response = {
            "success": True,
            "checkpoint": {
                "task_id": "task123",
                "current_state": "Implementation complete",
                "next_steps": ["Write tests", "Update documentation"]
            }
        }
        operation_factory._workflow_handler.checkpoint_work.return_value = expected_response
        
        result = operation_factory.handle_operation(
            "checkpoint_work",
            task_id="task123",
            current_state="Implementation complete",
            next_steps=["Write tests", "Update documentation"],
            notes="All core features implemented"
        )
        
        assert result == expected_response
        operation_factory._workflow_handler.checkpoint_work.assert_called_once_with(
            task_id="task123",
            current_state="Implementation complete",
            next_steps=["Write tests", "Update documentation"],
            notes="All core features implemented"
        )
    
    def test_checkpoint_work_minimal_params(self, operation_factory):
        """Test checkpoint with minimal parameters."""
        operation_factory._workflow_handler.checkpoint_work.return_value = {"success": True}
        
        result = operation_factory.handle_operation(
            "checkpoint_work",
            task_id="task123",
            current_state="In progress"
        )
        
        assert result["success"] is True
        operation_factory._workflow_handler.checkpoint_work.assert_called_once_with(
            task_id="task123",
            current_state="In progress",
            next_steps=None,
            notes=None
        )


class TestContextOperations:
    """Test context operations."""

    def test_update_work_context_success(self, operation_factory):
        """Test successful work context update."""
        expected_response = {
            "success": True,
            "context": {
                "task_id": "task123",
                "files_read": ["config.py", "main.py"],
                "files_modified": ["feature.py"],
                "key_decisions": ["Used strategy pattern"],
                "discoveries": ["Found existing utility functions"],
                "test_results": {"unit_tests": "passed", "integration_tests": "pending"}
            }
        }
        operation_factory._context_handler.update_work_context.return_value = expected_response
        
        result = operation_factory.handle_operation(
            "update_work_context",
            task_id="task123",
            files_read=["config.py", "main.py"],
            files_modified=["feature.py"],
            key_decisions=["Used strategy pattern"],
            discoveries=["Found existing utility functions"],
            test_results={"unit_tests": "passed", "integration_tests": "pending"}
        )
        
        assert result == expected_response
        operation_factory._context_handler.update_work_context.assert_called_once()
    
    def test_update_work_context_partial_data(self, operation_factory):
        """Test context update with partial data."""
        operation_factory._context_handler.update_work_context.return_value = {"success": True}
        
        result = operation_factory.handle_operation(
            "update_work_context",
            task_id="task123",
            files_modified=["feature.py", "test_feature.py"]
        )
        
        assert result["success"] is True
        operation_factory._context_handler.update_work_context.assert_called_once_with(
            task_id="task123",
            files_read=None,
            files_modified=["feature.py", "test_feature.py"],
            key_decisions=None,
            discoveries=None,
            test_results=None
        )


class TestErrorHandling:
    """Test error handling in operation factory."""

    def test_unknown_operation(self, operation_factory, mock_response_formatter):
        """Test handling of unknown operation."""
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Unknown operation: invalid_op",
            "error_code": ErrorCodes.INVALID_OPERATION
        }
        
        result = operation_factory.handle_operation("invalid_op", task_id="task123")
        
        assert result["success"] is False
        assert "Unknown operation" in result["error"]
        mock_response_formatter.create_error_response.assert_called_once()
        
        # Check that valid operations are included in metadata
        call_args = mock_response_formatter.create_error_response.call_args
        assert "metadata" in call_args[1]
        assert "valid_operations" in call_args[1]["metadata"]
    
    def test_handler_exception(self, operation_factory, mock_response_formatter):
        """Test exception handling from handlers."""
        # Make handler raise exception
        operation_factory._progress_handler.report_progress.side_effect = Exception("Handler error")
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Operation failed: Handler error",
            "error_code": ErrorCodes.OPERATION_FAILED
        }
        
        result = operation_factory.handle_operation(
            "report_progress",
            task_id="task123",
            description="Test"
        )
        
        assert result["success"] is False
        assert "Handler error" in result["error"]
    
    def test_invalid_workflow_operation(self, operation_factory, mock_response_formatter):
        """Test invalid workflow operation."""
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Unsupported workflow operation: invalid_workflow",
            "error_code": ErrorCodes.INVALID_OPERATION
        }
        
        # Override _handle_workflow_operation to test the else branch
        operation_factory.handle_operation = Mock(wraps=operation_factory.handle_operation)
        
        # Directly call the workflow handler with invalid operation
        result = operation_factory._handle_workflow_operation("invalid_workflow", task_id="task123")
        
        assert result["success"] is False
        assert "Unsupported workflow operation" in result["error"]
    
    def test_invalid_context_operation(self, operation_factory, mock_response_formatter):
        """Test invalid context operation."""
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Unsupported context operation: invalid_context",
            "error_code": ErrorCodes.INVALID_OPERATION
        }
        
        # Directly call the context handler with invalid operation
        result = operation_factory._handle_context_operation("invalid_context", task_id="task123")
        
        assert result["success"] is False
        assert "Unsupported context operation" in result["error"]


class TestOperationRouting:
    """Test operation routing to correct handlers."""

    def test_operation_routing_matrix(self, operation_factory):
        """Test that all operations route to correct handlers."""
        # Mock all handlers
        operation_factory._progress_handler.report_progress.return_value = {"handler": "progress", "method": "report"}
        operation_factory._progress_handler.quick_task_update.return_value = {"handler": "progress", "method": "quick"}
        operation_factory._workflow_handler.checkpoint_work.return_value = {"handler": "workflow", "method": "checkpoint"}
        operation_factory._context_handler.update_work_context.return_value = {"handler": "context", "method": "update"}
        
        # Test routing
        routing_tests = [
            ("report_progress", "progress", "report"),
            ("quick_task_update", "progress", "quick"),
            ("checkpoint_work", "workflow", "checkpoint"),
            ("update_work_context", "context", "update")
        ]
        
        for operation, expected_handler, expected_method in routing_tests:
            result = operation_factory.handle_operation(operation, task_id="test")
            assert result["handler"] == expected_handler
            assert result["method"] == expected_method
    
    def test_all_parameters_passed_through(self, operation_factory):
        """Test that all parameters are correctly passed to handlers."""
        # Complex test data
        test_data = {
            "task_id": "task123",
            "progress_type": "testing",
            "description": "Running tests",
            "percentage": 75,
            "files_affected": ["test1.py", "test2.py"],
            "next_steps": ["Deploy", "Monitor"],
            "status": "in_progress",
            "notes": "All unit tests passing",
            "completed_work": ["Unit tests", "Integration tests"],
            "current_state": "Testing phase",
            "files_read": ["spec.md", "requirements.txt"],
            "files_modified": ["test_suite.py"],
            "key_decisions": ["Use pytest framework"],
            "discoveries": ["Found edge case bug"],
            "test_results": {"coverage": "95%"}
        }
        
        operation_factory._progress_handler.report_progress.return_value = {"success": True}
        
        # Call with all parameters
        operation_factory.handle_operation("report_progress", **test_data)
        
        # Verify correct parameters were passed
        call_args = operation_factory._progress_handler.report_progress.call_args[1]
        assert call_args["task_id"] == "task123"
        assert call_args["progress_type"] == "testing"
        assert call_args["description"] == "Running tests"
        assert call_args["percentage"] == 75
        assert call_args["files_affected"] == ["test1.py", "test2.py"]
        assert call_args["next_steps"] == ["Deploy", "Monitor"]


class TestLogging:
    """Test logging functionality."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.logger')
    def test_initialization_logged(self, mock_logger, mock_response_formatter, mock_task_facade, mock_context_facade_factory):
        """Test that initialization is logged."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ProgressReportingHandler'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.WorkflowHandler'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.ContextHandler'):
            
            factory = ProgressOperationFactory(
                response_formatter=mock_response_formatter,
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            mock_logger.info.assert_called_with("ProgressOperationFactory initialized with modular handlers")
    
    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.factories.operation_factory.logger')
    def test_error_logged(self, mock_logger, operation_factory):
        """Test that errors are logged."""
        # Make handler raise exception
        operation_factory._progress_handler.report_progress.side_effect = Exception("Test error")
        
        operation_factory.handle_operation("report_progress", task_id="task123")
        
        mock_logger.error.assert_called()
        assert "Test error" in mock_logger.error.call_args[0][0]