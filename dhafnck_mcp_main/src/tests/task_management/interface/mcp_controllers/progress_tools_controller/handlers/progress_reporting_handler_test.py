"""
Tests for ProgressReportingHandler - Handles progress reporting and task update operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler import ProgressReportingHandler
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory


@pytest.fixture
def mock_response_formatter():
    """Create mock response formatter."""
    formatter = Mock(spec=StandardResponseFormatter)
    formatter.create_success_response.return_value = {
        "success": True,
        "message": "Success"
    }
    formatter.create_error_response.return_value = {
        "success": False,
        "error": "Test error"
    }
    return formatter


@pytest.fixture
def mock_task_facade():
    """Create mock task application facade."""
    facade = Mock(spec=TaskApplicationFacade)
    facade.update_task.return_value = {"success": True, "task": {"id": "task123"}}
    return facade


@pytest.fixture
def mock_context_facade_factory():
    """Create mock unified context facade factory."""
    factory = Mock(spec=UnifiedContextFacadeFactory)
    facade = Mock()
    facade.update_context.return_value = {"success": True}
    factory.create.return_value = facade
    return factory


@pytest.fixture
def progress_handler(mock_response_formatter, mock_task_facade, mock_context_facade_factory):
    """Create ProgressReportingHandler instance with mocked dependencies."""
    return ProgressReportingHandler(
        response_formatter=mock_response_formatter,
        task_facade=mock_task_facade,
        context_facade_factory=mock_context_facade_factory
    )


class TestProgressReportingHandler:
    """Test suite for ProgressReportingHandler."""

    def test_handler_initialization(self, mock_response_formatter, mock_task_facade, mock_context_facade_factory):
        """Test handler initialization with dependencies."""
        handler = ProgressReportingHandler(
            response_formatter=mock_response_formatter,
            task_facade=mock_task_facade,
            context_facade_factory=mock_context_facade_factory
        )
        
        assert handler._response_formatter == mock_response_formatter
        assert handler._task_facade == mock_task_facade
        assert handler._context_facade_factory == mock_context_facade_factory
        assert len(handler.VALID_PROGRESS_TYPES) > 0
        assert "implementation" in handler.VALID_PROGRESS_TYPES


class TestReportProgress:
    """Test report_progress functionality."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.datetime')
    def test_report_progress_success(self, mock_datetime, progress_handler, mock_context_facade_factory, mock_response_formatter):
        """Test successful progress reporting."""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Configure mock response
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "operation": "report_progress",
            "data": {
                "progress_type": "implementation",
                "percentage": 75,
                "next_reminder": "Progress will be tracked automatically",
                "hint": "Good progress! Remember to document key decisions."
            },
            "message": "Progress reported for task task123"
        }
        
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="implementation",
            description="Completed core functionality",
            percentage=75,
            files_affected=["main.py", "utils.py"],
            next_steps=["Write tests", "Update documentation"]
        )
        
        # Verify context facade was called
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.assert_called_once()
        call_args = context_facade.update_context.call_args
        
        assert call_args[1]["level"] == "task"
        assert call_args[1]["context_id"] == "task123"
        assert call_args[1]["data"]["progress"]["type"] == "implementation"
        assert call_args[1]["data"]["progress"]["description"] == "Completed core functionality"
        assert call_args[1]["data"]["progress"]["percentage"] == 75
        assert call_args[1]["data"]["files_affected"] == ["main.py", "utils.py"]
        assert call_args[1]["data"]["next_steps"] == ["Write tests", "Update documentation"]
        
        assert result["success"] is True
        assert "Good progress!" in result["data"]["hint"]

    def test_report_progress_invalid_type(self, progress_handler, mock_context_facade_factory):
        """Test progress reporting with invalid type."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.logger') as mock_logger:
            result = progress_handler.report_progress(
                task_id="task123",
                progress_type="invalid_type",
                description="Some progress"
            )
            
            # Should log warning but continue with "update" type
            mock_logger.warning.assert_called_once()
            
            # Verify context was updated with "update" type
            context_facade = mock_context_facade_factory.create.return_value
            call_args = context_facade.update_context.call_args
            assert call_args[1]["data"]["progress"]["type"] == "update"

    def test_report_progress_invalid_percentage(self, progress_handler, mock_response_formatter):
        """Test progress reporting with invalid percentage."""
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Invalid percentage value"
        }
        
        # Test percentage > 100
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Testing",
            percentage=150
        )
        
        assert result["success"] is False
        assert "Invalid percentage" in result["error"]
        
        # Test negative percentage
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Testing",
            percentage=-10
        )
        
        assert result["success"] is False

    def test_report_progress_minimal_data(self, progress_handler, mock_context_facade_factory):
        """Test progress reporting with minimal data."""
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="analysis",
            description="Started analysis"
        )
        
        # Verify only required fields are sent
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        context_data = call_args[1]["data"]
        
        assert "progress" in context_data
        assert "files_affected" not in context_data
        assert "next_steps" not in context_data
        assert context_data["progress"]["percentage"] is None

    def test_report_progress_high_percentage_hint(self, progress_handler, mock_response_formatter):
        """Test progress reporting with high percentage provides completion hint."""
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "percentage": 95,
                "hint": "Task is nearly complete. Consider running tests and preparing completion summary."
            }
        }
        
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="implementation",
            description="Almost done",
            percentage=95
        )
        
        assert "nearly complete" in result["data"]["hint"]
        assert "tests" in result["data"]["hint"]

    def test_report_progress_context_failure(self, progress_handler, mock_context_facade_factory, mock_response_formatter):
        """Test progress reporting when context update fails."""
        # Configure context update to fail
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.return_value = {
            "success": False,
            "error": "Context update failed"
        }
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to update progress: Context update failed"
        }
        
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Running tests"
        )
        
        assert result["success"] is False
        assert "Context update failed" in result["error"]

    def test_report_progress_exception(self, progress_handler, mock_context_facade_factory, mock_response_formatter):
        """Test progress reporting when exception occurs."""
        # Configure to raise exception
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.side_effect = Exception("Database error")
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to report progress: Database error"
        }
        
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="debugging",
            description="Debugging issue"
        )
        
        assert result["success"] is False
        assert "Database error" in result["error"]


class TestQuickTaskUpdate:
    """Test quick_task_update functionality."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.datetime')
    def test_quick_task_update_success(self, mock_datetime, progress_handler, mock_task_facade, mock_context_facade_factory, mock_response_formatter):
        """Test successful quick task update."""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "updated_fields": ["status", "quick_notes", "completed_work"],
                "status_updated": True,
                "context_updated": True
            },
            "message": "Task task123 updated successfully"
        }
        
        result = progress_handler.quick_task_update(
            task_id="task123",
            status="in_progress",
            notes="Started implementation",
            completed_work="Setup project structure"
        )
        
        # Verify task facade was called for status update
        mock_task_facade.update_task.assert_called_once_with(
            task_id="task123",
            status="in_progress"
        )
        
        # Verify context update
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.assert_called_once()
        call_args = context_facade.update_context.call_args
        context_data = call_args[1]["data"]
        
        assert context_data["status_change"]["new_status"] == "in_progress"
        assert context_data["quick_notes"]["notes"] == "Started implementation"
        assert context_data["completed_work"]["description"] == "Setup project structure"
        
        assert result["success"] is True
        assert result["data"]["status_updated"] is True
        assert result["data"]["context_updated"] is True

    def test_quick_task_update_status_only(self, progress_handler, mock_task_facade, mock_context_facade_factory):
        """Test quick update with only status change."""
        result = progress_handler.quick_task_update(
            task_id="task123",
            status="done"
        )
        
        # Verify task facade was called
        mock_task_facade.update_task.assert_called_once_with(
            task_id="task123",
            status="done"
        )
        
        # Verify context update includes status change
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        context_data = call_args[1]["data"]
        
        assert "status_change" in context_data
        assert "quick_notes" not in context_data
        assert "completed_work" not in context_data

    def test_quick_task_update_notes_only(self, progress_handler, mock_task_facade, mock_context_facade_factory):
        """Test quick update with only notes."""
        result = progress_handler.quick_task_update(
            task_id="task123",
            notes="Important discovery: found performance issue"
        )
        
        # Verify task facade was NOT called (no status change)
        mock_task_facade.update_task.assert_not_called()
        
        # Verify context update includes notes
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        context_data = call_args[1]["data"]
        
        assert "quick_notes" in context_data
        assert context_data["quick_notes"]["notes"] == "Important discovery: found performance issue"
        assert "status_change" not in context_data

    def test_quick_task_update_empty_params(self, progress_handler, mock_task_facade, mock_context_facade_factory, mock_response_formatter):
        """Test quick update with no parameters."""
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "updated_fields": [],
                "status_updated": False,
                "context_updated": False
            }
        }
        
        result = progress_handler.quick_task_update(task_id="task123")
        
        # Nothing should be updated
        mock_task_facade.update_task.assert_not_called()
        mock_context_facade_factory.create.return_value.update_context.assert_not_called()
        
        assert result["success"] is True
        assert result["data"]["status_updated"] is False
        assert result["data"]["context_updated"] is False

    def test_quick_task_update_task_failure(self, progress_handler, mock_task_facade, mock_response_formatter):
        """Test quick update when task update fails."""
        # Configure task update to fail
        mock_task_facade.update_task.return_value = {
            "success": False,
            "error": "Task not found"
        }
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to update task: Task not found"
        }
        
        result = progress_handler.quick_task_update(
            task_id="nonexistent",
            status="done"
        )
        
        assert result["success"] is False
        assert "Task not found" in result["error"]

    def test_quick_task_update_context_failure_warning(self, progress_handler, mock_task_facade, mock_context_facade_factory):
        """Test quick update continues when context update fails."""
        # Configure context update to fail
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.return_value = {
            "success": False,
            "error": "Context service unavailable"
        }
        
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.logger') as mock_logger:
            result = progress_handler.quick_task_update(
                task_id="task123",
                notes="Some notes"
            )
            
            # Should log warning but continue
            mock_logger.warning.assert_called_once()
            assert "Context update failed" in mock_logger.warning.call_args[0][0]
            
            # Operation should still succeed
            assert result["success"] is True

    def test_quick_task_update_exception(self, progress_handler, mock_task_facade, mock_response_formatter):
        """Test quick update when exception occurs."""
        # Configure to raise exception
        mock_task_facade.update_task.side_effect = Exception("Database connection lost")
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to update task: Database connection lost"
        }
        
        result = progress_handler.quick_task_update(
            task_id="task123",
            status="blocked"
        )
        
        assert result["success"] is False
        assert "Database connection lost" in result["error"]


class TestValidProgressTypes:
    """Test valid progress types validation."""

    def test_all_valid_progress_types(self, progress_handler):
        """Test all valid progress types are accepted."""
        valid_types = [
            "analysis", "implementation", "testing", "debugging", "documentation",
            "review", "research", "planning", "integration", "deployment"
        ]
        
        for progress_type in valid_types:
            result = progress_handler.report_progress(
                task_id="task123",
                progress_type=progress_type,
                description=f"Working on {progress_type}"
            )
            
            # All should succeed
            assert result["success"] is True

    def test_case_sensitive_progress_type(self, progress_handler):
        """Test progress type is case sensitive."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.logger') as mock_logger:
            result = progress_handler.report_progress(
                task_id="task123",
                progress_type="IMPLEMENTATION",  # Wrong case
                description="Working"
            )
            
            # Should log warning about unknown type
            mock_logger.warning.assert_called_once()


class TestLogging:
    """Test logging in progress reporting handler."""

    def test_error_logging_report_progress(self, progress_handler, mock_context_facade_factory):
        """Test error logging in report_progress."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.logger') as mock_logger:
            # Make context update raise exception
            context_facade = mock_context_facade_factory.create.return_value
            context_facade.update_context.side_effect = RuntimeError("Runtime error")
            
            progress_handler.report_progress(
                task_id="task123",
                progress_type="testing",
                description="Testing"
            )
            
            mock_logger.error.assert_called_once()
            assert "Error reporting progress for task task123" in mock_logger.error.call_args[0][0]

    def test_error_logging_quick_update(self, progress_handler, mock_task_facade):
        """Test error logging in quick_task_update."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.progress_reporting_handler.logger') as mock_logger:
            # Make task update raise exception
            mock_task_facade.update_task.side_effect = ValueError("Invalid status")
            
            progress_handler.quick_task_update(
                task_id="task123",
                status="invalid_status"
            )
            
            mock_logger.error.assert_called_once()
            assert "Error in quick task update for task123" in mock_logger.error.call_args[0][0]


class TestEdgeCases:
    """Test edge cases in progress reporting handler."""

    def test_report_progress_zero_percentage(self, progress_handler):
        """Test progress reporting with 0% completion."""
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="planning",
            description="Starting planning phase",
            percentage=0
        )
        
        assert result["success"] is True
        assert result["data"]["percentage"] == 0

    def test_report_progress_100_percentage(self, progress_handler, mock_response_formatter):
        """Test progress reporting with 100% completion."""
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "percentage": 100,
                "hint": "Task is nearly complete. Consider running tests and preparing completion summary."
            }
        }
        
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="implementation",
            description="Implementation complete",
            percentage=100
        )
        
        assert result["success"] is True
        assert "nearly complete" in result["data"]["hint"]

    def test_report_progress_empty_lists(self, progress_handler):
        """Test progress reporting with empty lists."""
        result = progress_handler.report_progress(
            task_id="task123",
            progress_type="review",
            description="Starting review",
            files_affected=[],
            next_steps=[]
        )
        
        # Should handle empty lists without issues
        assert result["success"] is True

    def test_quick_update_long_notes(self, progress_handler, mock_context_facade_factory):
        """Test quick update with very long notes."""
        long_notes = "A" * 10000  # Very long notes
        
        result = progress_handler.quick_task_update(
            task_id="task123",
            notes=long_notes
        )
        
        # Should handle long notes without truncation
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        assert call_args[1]["data"]["quick_notes"]["notes"] == long_notes