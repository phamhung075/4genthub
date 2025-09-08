"""
Tests for Context Handler

Tests the handler responsible for work context updates and structured information management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.context_handler import (
    ContextHandler
)
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter, ResponseStatus, ErrorCodes


@pytest.fixture
def mock_response_formatter():
    """Create mock response formatter."""
    formatter = Mock(spec=StandardResponseFormatter)
    
    def create_success_response(operation, data, message, metadata=None):
        return {
            "success": True,
            "status": ResponseStatus.SUCCESS,
            "operation": operation,
            "data": data,
            "message": message,
            "metadata": metadata or {}
        }
    
    def create_error_response(operation, error, error_code, metadata=None):
        return {
            "success": False,
            "status": ResponseStatus.ERROR,
            "operation": operation,
            "error": error,
            "error_code": error_code,
            "metadata": metadata or {}
        }
    
    formatter.create_success_response.side_effect = create_success_response
    formatter.create_error_response.side_effect = create_error_response
    return formatter


@pytest.fixture
def mock_context_facade():
    """Create mock context facade."""
    facade = Mock()
    facade.update_context.return_value = {"success": True, "context": {}}
    return facade


@pytest.fixture
def mock_context_facade_factory(mock_context_facade):
    """Create mock context facade factory."""
    factory = Mock()
    factory.create.return_value = mock_context_facade
    return factory


@pytest.fixture
def context_handler(mock_response_formatter, mock_context_facade_factory):
    """Create ContextHandler instance with mocked dependencies."""
    return ContextHandler(
        response_formatter=mock_response_formatter,
        context_facade_factory=mock_context_facade_factory
    )


class TestContextHandlerInitialization:
    """Test ContextHandler initialization."""

    def test_handler_initialization(self, mock_response_formatter, mock_context_facade_factory):
        """Test handler initialization with dependencies."""
        handler = ContextHandler(
            response_formatter=mock_response_formatter,
            context_facade_factory=mock_context_facade_factory
        )
        
        assert handler._response_formatter == mock_response_formatter
        assert handler._context_facade_factory == mock_context_facade_factory


class TestUpdateWorkContext:
    """Test update_work_context functionality."""

    def test_update_context_with_all_fields(self, context_handler, mock_context_facade_factory, mock_context_facade):
        """Test updating context with all field types."""
        # Test data
        files_read = ["config.py", "utils.py", "main.py"]
        files_modified = ["feature.py", "test_feature.py"]
        key_decisions = ["Use strategy pattern", "Implement caching", "Add retry logic"]
        discoveries = ["Found existing utility", "API rate limit is 100/min"]
        test_results = {
            "unit_tests": {"passed": 45, "failed": 0},
            "integration_tests": {"passed": 10, "failed": 2},
            "coverage": "87%"
        }
        
        result = context_handler.update_work_context(
            task_id="task123",
            files_read=files_read,
            files_modified=files_modified,
            key_decisions=key_decisions,
            discoveries=discoveries,
            test_results=test_results
        )
        
        assert result["success"] is True
        assert result["operation"] == "update_work_context"
        assert result["data"]["files_count"] == 5  # 3 read + 2 modified
        assert result["data"]["decisions_count"] == 3
        assert result["data"]["discoveries_count"] == 2
        assert result["data"]["has_test_results"] is True
        assert result["data"]["context_updated"] is True
        assert "5 files, 3 decisions, 2 discoveries, test results" in result["message"]
        
        # Verify facade was called correctly
        mock_context_facade.update_context.assert_called_once()
        call_args = mock_context_facade.update_context.call_args[1]
        assert call_args["level"] == "task"
        assert call_args["context_id"] == "task123"
        assert call_args["propagate_changes"] is True
        
        # Check context data structure
        context_data = call_args["data"]
        assert "work_context" in context_data
        assert context_data["work_context"]["files_read"] == files_read
        assert context_data["work_context"]["files_modified"] == files_modified
        assert context_data["work_context"]["key_decisions"] == key_decisions
        assert context_data["work_context"]["discoveries"] == discoveries
        assert context_data["work_context"]["test_results"] == test_results
    
    def test_update_context_with_files_only(self, context_handler, mock_context_facade):
        """Test updating context with only file information."""
        result = context_handler.update_work_context(
            task_id="task123",
            files_read=["readme.md"],
            files_modified=["config.json", "settings.py"]
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 3
        assert result["data"]["decisions_count"] == 0
        assert result["data"]["discoveries_count"] == 0
        assert result["data"]["has_test_results"] is False
        assert "3 files" in result["message"]
        assert "decisions" not in result["message"]
    
    def test_update_context_with_decisions_only(self, context_handler, mock_context_facade):
        """Test updating context with only decisions."""
        key_decisions = ["Use async/await pattern", "Implement circuit breaker"]
        
        result = context_handler.update_work_context(
            task_id="task123",
            key_decisions=key_decisions
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 0
        assert result["data"]["decisions_count"] == 2
        assert result["data"]["discoveries_count"] == 0
        assert "2 decisions" in result["message"]
        assert "files" not in result["message"]
    
    def test_update_context_with_empty_lists(self, context_handler, mock_context_facade):
        """Test updating context with empty lists."""
        result = context_handler.update_work_context(
            task_id="task123",
            files_read=[],
            files_modified=[],
            key_decisions=[],
            discoveries=[]
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 0
        assert result["data"]["decisions_count"] == 0
        assert result["data"]["discoveries_count"] == 0
        
        # Check that empty lists are not included in context data
        call_args = mock_context_facade.update_context.call_args[1]
        context_data = call_args["data"]["work_context"]
        assert "files_read" not in context_data
        assert "files_modified" not in context_data
        assert "key_decisions" not in context_data
        assert "discoveries" not in context_data
    
    def test_update_context_with_complex_test_results(self, context_handler, mock_context_facade):
        """Test updating context with complex test results structure."""
        test_results = {
            "unit_tests": {
                "total": 50,
                "passed": 48,
                "failed": 2,
                "skipped": 0,
                "failures": [
                    {"test": "test_edge_case", "error": "AssertionError"},
                    {"test": "test_null_input", "error": "TypeError"}
                ]
            },
            "performance": {
                "response_time_ms": 125,
                "memory_usage_mb": 64,
                "cpu_usage_percent": 35
            },
            "test_run": {
                "duration_seconds": 45.6,
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }
        
        result = context_handler.update_work_context(
            task_id="task123",
            test_results=test_results
        )
        
        assert result["success"] is True
        assert result["data"]["has_test_results"] is True
        assert "test results" in result["message"]
        
        # Verify test results were passed correctly
        call_args = mock_context_facade.update_context.call_args[1]
        assert call_args["data"]["work_context"]["test_results"] == test_results
    
    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.context_handler.datetime')
    def test_update_context_timestamp(self, mock_datetime, context_handler, mock_context_facade):
        """Test that timestamp is included in context update."""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        result = context_handler.update_work_context(
            task_id="task123",
            discoveries=["Found optimization opportunity"]
        )
        
        assert result["success"] is True
        
        # Check timestamp was included
        call_args = mock_context_facade.update_context.call_args[1]
        context_data = call_args["data"]["work_context"]
        assert context_data["timestamp"] == "2024-01-01T12:00:00+00:00"
    
    def test_update_context_failure(self, context_handler, mock_context_facade):
        """Test handling of context update failure."""
        # Mock facade failure
        mock_context_facade.update_context.return_value = {
            "success": False,
            "error": "Context not found"
        }
        
        result = context_handler.update_work_context(
            task_id="task123",
            files_modified=["feature.py"]
        )
        
        assert result["success"] is False
        assert result["operation"] == "update_work_context"
        assert "Failed to update work context: Context not found" in result["error"]
        assert result["error_code"] == ErrorCodes.OPERATION_FAILED
        assert result["metadata"]["task_id"] == "task123"
    
    def test_update_context_exception(self, context_handler, mock_context_facade):
        """Test exception handling in context update."""
        # Mock exception
        mock_context_facade.update_context.side_effect = Exception("Database connection error")
        
        result = context_handler.update_work_context(
            task_id="task123",
            key_decisions=["Use microservices"]
        )
        
        assert result["success"] is False
        assert result["operation"] == "update_work_context"
        assert "Work context update failed: Database connection error" in result["error"]
        assert result["error_code"] == ErrorCodes.INTERNAL_ERROR
        assert result["metadata"]["task_id"] == "task123"
    
    def test_update_context_with_none_values(self, context_handler, mock_context_facade):
        """Test that None values are handled correctly."""
        result = context_handler.update_work_context(
            task_id="task123",
            files_read=None,
            files_modified=None,
            key_decisions=None,
            discoveries=None,
            test_results=None
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 0
        assert result["data"]["decisions_count"] == 0
        assert result["data"]["discoveries_count"] == 0
        assert result["data"]["has_test_results"] is False
        
        # Check that only timestamp is in context data
        call_args = mock_context_facade.update_context.call_args[1]
        context_data = call_args["data"]["work_context"]
        assert "timestamp" in context_data
        assert len(context_data) == 1  # Only timestamp
    
    def test_update_context_metadata_hints(self, context_handler, mock_context_facade):
        """Test that proper hints are included in metadata."""
        result = context_handler.update_work_context(
            task_id="task123",
            discoveries=["API supports batch operations"]
        )
        
        assert result["success"] is True
        assert result["metadata"]["task_id"] == "task123"
        assert "hint" in result["metadata"]
        assert "Information will be available for future sessions" in result["metadata"]["hint"]


class TestContextHandlerEdgeCases:
    """Test edge cases for ContextHandler."""

    def test_update_context_with_special_characters(self, context_handler, mock_context_facade):
        """Test handling of special characters in context data."""
        files_modified = ["file with spaces.py", "file-with-dashes.js", "file_with_underscores.ts"]
        key_decisions = ["Use 'single quotes'", 'Use "double quotes"', "Use `backticks`"]
        
        result = context_handler.update_work_context(
            task_id="task123",
            files_modified=files_modified,
            key_decisions=key_decisions
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 3
        assert result["data"]["decisions_count"] == 3
        
        # Verify data was passed correctly
        call_args = mock_context_facade.update_context.call_args[1]
        context_data = call_args["data"]["work_context"]
        assert context_data["files_modified"] == files_modified
        assert context_data["key_decisions"] == key_decisions
    
    def test_update_context_with_large_data(self, context_handler, mock_context_facade):
        """Test handling of large data sets."""
        # Generate large lists
        files_read = [f"file_{i}.py" for i in range(100)]
        discoveries = [f"Discovery {i}: Important finding about component {i}" for i in range(50)]
        
        result = context_handler.update_work_context(
            task_id="task123",
            files_read=files_read,
            discoveries=discoveries
        )
        
        assert result["success"] is True
        assert result["data"]["files_count"] == 100
        assert result["data"]["discoveries_count"] == 50
        assert "100 files, 50 discoveries" in result["message"]
    
    def test_update_context_with_nested_test_results(self, context_handler, mock_context_facade):
        """Test handling of deeply nested test results."""
        test_results = {
            "test_suites": {
                "unit": {
                    "modules": {
                        "auth": {"passed": 10, "failed": 0},
                        "api": {"passed": 20, "failed": 1},
                        "database": {"passed": 15, "failed": 0}
                    }
                },
                "integration": {
                    "scenarios": {
                        "user_flow": {"status": "passed"},
                        "payment_flow": {"status": "failed", "reason": "Timeout"}
                    }
                }
            },
            "metrics": {
                "coverage": {
                    "lines": 85.5,
                    "branches": 78.2,
                    "functions": 92.1
                }
            }
        }
        
        result = context_handler.update_work_context(
            task_id="task123",
            test_results=test_results
        )
        
        assert result["success"] is True
        assert result["data"]["has_test_results"] is True
        
        # Verify nested structure was preserved
        call_args = mock_context_facade.update_context.call_args[1]
        assert call_args["data"]["work_context"]["test_results"] == test_results


class TestContextHandlerIntegration:
    """Test integration scenarios for ContextHandler."""

    def test_multiple_context_updates(self, context_handler, mock_context_facade):
        """Test multiple context updates in sequence."""
        # First update
        result1 = context_handler.update_work_context(
            task_id="task123",
            files_read=["spec.md", "requirements.txt"]
        )
        
        assert result1["success"] is True
        assert mock_context_facade.update_context.call_count == 1
        
        # Second update
        result2 = context_handler.update_work_context(
            task_id="task123",
            files_modified=["implementation.py"],
            key_decisions=["Implement async pattern"]
        )
        
        assert result2["success"] is True
        assert mock_context_facade.update_context.call_count == 2
        
        # Third update
        result3 = context_handler.update_work_context(
            task_id="task123",
            test_results={"tests_passed": True}
        )
        
        assert result3["success"] is True
        assert mock_context_facade.update_context.call_count == 3
    
    def test_context_facade_factory_usage(self, mock_response_formatter, mock_context_facade_factory, mock_context_facade):
        """Test that context facade factory is used correctly."""
        handler = ContextHandler(
            response_formatter=mock_response_formatter,
            context_facade_factory=mock_context_facade_factory
        )
        
        result = handler.update_work_context(
            task_id="task123",
            discoveries=["Found reusable component"]
        )
        
        assert result["success"] is True
        
        # Verify factory was called to create facade
        mock_context_facade_factory.create.assert_called_once()
        
        # Verify facade was used
        mock_context_facade.update_context.assert_called_once()


class TestContextHandlerLogging:
    """Test logging functionality for ContextHandler."""

    @patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.handlers.context_handler.logger')
    def test_error_logging(self, mock_logger, context_handler, mock_context_facade):
        """Test that errors are properly logged."""
        # Mock exception
        error_msg = "Critical database failure"
        mock_context_facade.update_context.side_effect = Exception(error_msg)
        
        result = context_handler.update_work_context(
            task_id="task123",
            files_modified=["critical_file.py"]
        )
        
        assert result["success"] is False
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        assert "task123" in log_message
        assert error_msg in log_message