"""
Tests for WorkflowHandler - Handles workflow checkpoint and work state management operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.workflow_handler import WorkflowHandler
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes
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
def mock_context_facade_factory():
    """Create mock unified context facade factory."""
    factory = Mock(spec=UnifiedContextFacadeFactory)
    facade = Mock()
    facade.update_context.return_value = {"success": True}
    factory.create.return_value = facade
    return factory


@pytest.fixture
def workflow_handler(mock_response_formatter, mock_context_facade_factory):
    """Create WorkflowHandler instance with mocked dependencies."""
    return WorkflowHandler(
        response_formatter=mock_response_formatter,
        context_facade_factory=mock_context_facade_factory
    )


class TestWorkflowHandler:
    """Test suite for WorkflowHandler."""

    def test_handler_initialization(self, mock_response_formatter, mock_context_facade_factory):
        """Test handler initialization with dependencies."""
        handler = WorkflowHandler(
            response_formatter=mock_response_formatter,
            context_facade_factory=mock_context_facade_factory
        )
        
        assert handler._response_formatter == mock_response_formatter
        assert handler._context_facade_factory == mock_context_facade_factory


class TestCheckpointWork:
    """Test checkpoint_work functionality."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.workflow_handler.datetime')
    def test_checkpoint_work_success(self, mock_datetime, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test successful work checkpoint creation."""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # Configure mock response
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "operation": "checkpoint_work",
            "data": {
                "checkpoint_time": mock_now.isoformat(),
                "next_steps_count": 3,
                "has_notes": True
            },
            "message": "Work checkpoint created",
            "metadata": {
                "task_id": "task123",
                "hint": "Checkpoint saved. You can resume from this state later."
            }
        }
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Implementation 50% complete",
            next_steps=["Complete unit tests", "Add error handling", "Update documentation"],
            notes="Core functionality implemented, ready for testing phase"
        )
        
        # Verify context facade was called
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.assert_called_once_with(
            level="task",
            context_id="task123",
            data={
                "checkpoint": {
                    "timestamp": mock_now.isoformat(),
                    "current_state": "Implementation 50% complete",
                    "next_steps": ["Complete unit tests", "Add error handling", "Update documentation"],
                    "notes": "Core functionality implemented, ready for testing phase"
                }
            },
            propagate_changes=True
        )
        
        # Verify response
        assert result["success"] is True
        assert result["data"]["checkpoint_time"] == mock_now.isoformat()
        assert result["data"]["next_steps_count"] == 3
        assert result["data"]["has_notes"] is True
        assert "Checkpoint saved" in result["metadata"]["hint"]

    def test_checkpoint_work_without_notes(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint creation without notes."""
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Analysis complete",
            next_steps=["Start implementation", "Setup project structure"]
        )
        
        # Verify notes field is not included when not provided
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        checkpoint_data = call_args[1]["data"]["checkpoint"]
        
        assert "notes" not in checkpoint_data
        assert checkpoint_data["current_state"] == "Analysis complete"
        assert len(checkpoint_data["next_steps"]) == 2
        
        assert result["success"] is True

    def test_checkpoint_work_empty_next_steps(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test checkpoint creation with empty next steps list."""
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "next_steps_count": 0,
                "has_notes": False
            }
        }
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Task completed",
            next_steps=[]
        )
        
        # Should handle empty list without issues
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        checkpoint_data = call_args[1]["data"]["checkpoint"]
        
        assert checkpoint_data["next_steps"] == []
        assert result["success"] is True
        assert result["data"]["next_steps_count"] == 0

    def test_checkpoint_work_context_failure(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test checkpoint creation when context update fails."""
        # Configure context update to fail
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.return_value = {
            "success": False,
            "error": "Context service unavailable"
        }
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Failed to create checkpoint: Context service unavailable"
        }
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="In progress",
            next_steps=["Continue work"]
        )
        
        assert result["success"] is False
        assert "Context service unavailable" in result["error"]
        
        # Verify error formatter was called
        mock_response_formatter.create_error_response.assert_called_once_with(
            operation="checkpoint_work",
            error="Failed to create checkpoint: Context service unavailable",
            error_code=ErrorCodes.OPERATION_FAILED,
            metadata={"task_id": "task123"}
        )

    def test_checkpoint_work_exception(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test checkpoint creation when exception occurs."""
        # Configure to raise exception
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.side_effect = Exception("Database connection lost")
        
        mock_response_formatter.create_error_response.return_value = {
            "success": False,
            "error": "Checkpoint creation failed: Database connection lost"
        }
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Working",
            next_steps=["Next step"]
        )
        
        assert result["success"] is False
        assert "Database connection lost" in result["error"]


class TestDataValidation:
    """Test data validation in workflow handler."""

    def test_checkpoint_with_long_state_description(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint with very long state description."""
        long_state = "A" * 10000  # Very long state description
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state=long_state,
            next_steps=["Next step"]
        )
        
        # Should handle long text without issues
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        assert call_args[1]["data"]["checkpoint"]["current_state"] == long_state
        assert result["success"] is True

    def test_checkpoint_with_many_next_steps(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test checkpoint with many next steps."""
        many_steps = [f"Step {i}" for i in range(100)]
        
        mock_response_formatter.create_success_response.return_value = {
            "success": True,
            "data": {
                "next_steps_count": 100
            }
        }
        
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Planning complete",
            next_steps=many_steps
        )
        
        assert result["success"] is True
        assert result["data"]["next_steps_count"] == 100

    def test_checkpoint_with_special_characters(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint with special characters in data."""
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Working on 'feature' with \"quotes\"",
            next_steps=["Handle \n newlines", "Process \t tabs", "Support émojis 🚀"],
            notes="Special chars: < > & ' \" \\ /"
        )
        
        # Should handle special characters without issues
        assert result["success"] is True


class TestTimestamp:
    """Test timestamp handling in workflow handler."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.workflow_handler.datetime')
    def test_checkpoint_timestamp_utc(self, mock_datetime, workflow_handler, mock_context_facade_factory):
        """Test checkpoint uses UTC timestamp."""
        # Mock specific UTC time
        mock_utc_time = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_utc_time
        
        workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Working",
            next_steps=["Continue"]
        )
        
        # Verify UTC was used
        mock_datetime.now.assert_called_once_with(timezone.utc)
        
        # Verify timestamp in data
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        assert call_args[1]["data"]["checkpoint"]["timestamp"] == mock_utc_time.isoformat()

    def test_checkpoint_timestamp_format(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint timestamp is in ISO format."""
        workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Testing",
            next_steps=["Deploy"]
        )
        
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        timestamp = call_args[1]["data"]["checkpoint"]["timestamp"]
        
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


class TestLogging:
    """Test logging in workflow handler."""

    def test_error_logging(self, workflow_handler, mock_context_facade_factory):
        """Test that errors are logged."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.workflow_handler.logger') as mock_logger:
            # Make context update raise exception
            context_facade = mock_context_facade_factory.create.return_value
            context_facade.update_context.side_effect = RuntimeError("Runtime error")
            
            workflow_handler.checkpoint_work(
                task_id="task123",
                current_state="Error state",
                next_steps=["Fix error"]
            )
            
            mock_logger.error.assert_called_once()
            log_message = mock_logger.error.call_args[0][0]
            assert "Error creating checkpoint for task task123" in log_message
            assert "Runtime error" in log_message

    def test_no_logging_on_success(self, workflow_handler, mock_context_facade_factory):
        """Test that successful operations don't log errors."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.workflow_handler.logger') as mock_logger:
            workflow_handler.checkpoint_work(
                task_id="task123",
                current_state="All good",
                next_steps=["Continue"]
            )
            
            mock_logger.error.assert_not_called()


class TestResponseMetadata:
    """Test response metadata in workflow handler."""

    def test_success_response_metadata(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test success response includes proper metadata."""
        workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Working",
            next_steps=["Next"],
            notes="Progress notes"
        )
        
        # Verify response formatter was called with metadata
        mock_response_formatter.create_success_response.assert_called_once()
        call_args = mock_response_formatter.create_success_response.call_args
        
        assert call_args[1]["metadata"]["task_id"] == "task123"
        assert "resume from this state" in call_args[1]["metadata"]["hint"]

    def test_error_response_metadata(self, workflow_handler, mock_context_facade_factory, mock_response_formatter):
        """Test error response includes task ID in metadata."""
        # Make context update fail
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.return_value = {"success": False, "error": "Failed"}
        
        workflow_handler.checkpoint_work(
            task_id="task456",
            current_state="Failed state",
            next_steps=["Retry"]
        )
        
        # Verify error formatter includes task ID
        mock_response_formatter.create_error_response.assert_called_once()
        call_args = mock_response_formatter.create_error_response.call_args
        assert call_args[1]["metadata"]["task_id"] == "task456"


class TestEdgeCases:
    """Test edge cases in workflow handler."""

    def test_checkpoint_empty_task_id(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint with empty task ID."""
        result = workflow_handler.checkpoint_work(
            task_id="",
            current_state="State",
            next_steps=["Step"]
        )
        
        # Should still process (validation done elsewhere)
        context_facade = mock_context_facade_factory.create.return_value
        context_facade.update_context.assert_called_once()
        assert result["success"] is True

    def test_checkpoint_unicode_content(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint with unicode content."""
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="Working on internationalization: 中文, العربية, हिन्दी",
            next_steps=["Add more languages: 日本語, 한국어"],
            notes="Unicode test: 🌍🌎🌏"
        )
        
        # Should handle unicode without issues
        assert result["success"] is True

    def test_checkpoint_none_notes_explicit(self, workflow_handler, mock_context_facade_factory):
        """Test checkpoint with explicitly None notes."""
        result = workflow_handler.checkpoint_work(
            task_id="task123",
            current_state="State",
            next_steps=["Step"],
            notes=None
        )
        
        # Should handle None same as not provided
        context_facade = mock_context_facade_factory.create.return_value
        call_args = context_facade.update_context.call_args
        assert "notes" not in call_args[1]["data"]["checkpoint"]
        assert result["success"] is True