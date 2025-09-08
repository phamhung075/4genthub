"""
Tests for ProgressToolsController - Modular Implementation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, List

from fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller import ProgressToolsController
from fastmcp.task_management.application.facades.task_application_facade import TaskApplicationFacade
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory


@pytest.fixture
def mock_task_facade():
    """Create mock task application facade."""
    facade = Mock(spec=TaskApplicationFacade)
    return facade


@pytest.fixture
def mock_context_facade_factory():
    """Create mock unified context facade factory."""
    factory = Mock(spec=UnifiedContextFacadeFactory)
    return factory


@pytest.fixture
def mock_operation_factory():
    """Create mock operation factory."""
    with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory') as mock_factory_class:
        factory_instance = Mock()
        factory_instance.handle_operation.return_value = {"success": True}
        mock_factory_class.return_value = factory_instance
        yield factory_instance


@pytest.fixture
def progress_controller(mock_task_facade, mock_context_facade_factory, mock_operation_factory):
    """Create ProgressToolsController instance with mocked dependencies."""
    with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter'):
        controller = ProgressToolsController(
            task_facade=mock_task_facade,
            context_facade_factory=mock_context_facade_factory
        )
        controller._operation_factory = mock_operation_factory
        return controller


class TestProgressToolsController:
    """Test suite for ProgressToolsController."""

    def test_controller_initialization_with_dependencies(self, mock_task_facade, mock_context_facade_factory):
        """Test controller initialization with provided dependencies."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory'):
            
            controller = ProgressToolsController(
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            assert controller._task_facade == mock_task_facade
            assert controller._context_facade_factory == mock_context_facade_factory

    def test_controller_initialization_without_context_factory(self, mock_task_facade):
        """Test controller initialization using FacadeService when no context factory provided."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.FacadeService') as mock_facade_service:
            
            mock_facade_service.get_instance.return_value = Mock()
            
            controller = ProgressToolsController(task_facade=mock_task_facade)
            
            mock_facade_service.get_instance.assert_called_once()
            assert controller._task_facade == mock_task_facade

    def test_initialization_logging(self, mock_task_facade, mock_context_facade_factory):
        """Test that initialization is logged."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.logger') as mock_logger, \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter'), \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory'):
            
            controller = ProgressToolsController(
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            mock_logger.info.assert_called_with("ProgressToolsController initialized with modular architecture for Vision System Phase 2")


class TestReportProgress:
    """Test report_progress method."""

    def test_report_progress_delegates_to_factory(self, progress_controller, mock_operation_factory):
        """Test report_progress delegates to operation factory."""
        mock_operation_factory.handle_operation.return_value = {
            "success": True,
            "message": "Progress reported"
        }
        
        result = progress_controller.report_progress(
            task_id="task123",
            progress_type="implementation",
            description="Working on feature X",
            percentage=75,
            files_affected=["file1.py", "file2.py"],
            next_steps=["Write tests", "Add documentation"]
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="report_progress",
            task_id="task123",
            progress_type="implementation",
            description="Working on feature X",
            percentage=75,
            files_affected=["file1.py", "file2.py"],
            next_steps=["Write tests", "Add documentation"]
        )
        
        assert result["success"] is True
        assert result["message"] == "Progress reported"

    def test_report_progress_minimal_parameters(self, progress_controller, mock_operation_factory):
        """Test report_progress with only required parameters."""
        result = progress_controller.report_progress(
            task_id="task123",
            progress_type="analysis",
            description="Analyzing requirements"
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="report_progress",
            task_id="task123",
            progress_type="analysis",
            description="Analyzing requirements",
            percentage=None,
            files_affected=None,
            next_steps=None
        )

    def test_report_progress_all_optional_parameters(self, progress_controller, mock_operation_factory):
        """Test report_progress with all optional parameters."""
        result = progress_controller.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Running unit tests",
            percentage=90,
            files_affected=["test_module.py"],
            next_steps=["Run integration tests"]
        )
        
        assert mock_operation_factory.handle_operation.call_count == 1
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["percentage"] == 90
        assert call_kwargs["files_affected"] == ["test_module.py"]
        assert call_kwargs["next_steps"] == ["Run integration tests"]


class TestQuickTaskUpdate:
    """Test quick_task_update method."""

    def test_quick_task_update_delegates_to_factory(self, progress_controller, mock_operation_factory):
        """Test quick_task_update delegates to operation factory."""
        mock_operation_factory.handle_operation.return_value = {
            "success": True,
            "message": "Task updated"
        }
        
        result = progress_controller.quick_task_update(
            task_id="task123",
            status="in_progress",
            notes="Found a bug, investigating",
            completed_work="Fixed authentication issue"
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="quick_task_update",
            task_id="task123",
            status="in_progress",
            notes="Found a bug, investigating",
            completed_work="Fixed authentication issue"
        )
        
        assert result["success"] is True

    def test_quick_task_update_only_task_id(self, progress_controller, mock_operation_factory):
        """Test quick_task_update with only task_id."""
        result = progress_controller.quick_task_update(task_id="task123")
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="quick_task_update",
            task_id="task123",
            status=None,
            notes=None,
            completed_work=None
        )

    def test_quick_task_update_partial_parameters(self, progress_controller, mock_operation_factory):
        """Test quick_task_update with partial parameters."""
        result = progress_controller.quick_task_update(
            task_id="task123",
            status="done",
            notes="Task completed successfully"
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["status"] == "done"
        assert call_kwargs["notes"] == "Task completed successfully"
        assert call_kwargs["completed_work"] is None


class TestCheckpointWork:
    """Test checkpoint_work method."""

    def test_checkpoint_work_delegates_to_factory(self, progress_controller, mock_operation_factory):
        """Test checkpoint_work delegates to operation factory."""
        mock_operation_factory.handle_operation.return_value = {
            "success": True,
            "message": "Checkpoint created"
        }
        
        result = progress_controller.checkpoint_work(
            task_id="task123",
            current_state="Implementation 70% complete",
            next_steps=["Finish implementation", "Write tests"],
            notes="Core logic implemented"
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="checkpoint_work",
            task_id="task123",
            current_state="Implementation 70% complete",
            next_steps=["Finish implementation", "Write tests"],
            notes="Core logic implemented"
        )
        
        assert result["success"] is True

    def test_checkpoint_work_without_notes(self, progress_controller, mock_operation_factory):
        """Test checkpoint_work without optional notes."""
        result = progress_controller.checkpoint_work(
            task_id="task123",
            current_state="Testing phase",
            next_steps=["Run more tests", "Fix bugs"]
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="checkpoint_work",
            task_id="task123",
            current_state="Testing phase",
            next_steps=["Run more tests", "Fix bugs"],
            notes=None
        )

    def test_checkpoint_work_empty_next_steps(self, progress_controller, mock_operation_factory):
        """Test checkpoint_work with empty next steps list."""
        result = progress_controller.checkpoint_work(
            task_id="task123",
            current_state="Task completed",
            next_steps=[]
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["next_steps"] == []


class TestUpdateWorkContext:
    """Test update_work_context method."""

    def test_update_work_context_delegates_to_factory(self, progress_controller, mock_operation_factory):
        """Test update_work_context delegates to operation factory."""
        mock_operation_factory.handle_operation.return_value = {
            "success": True,
            "message": "Context updated"
        }
        
        result = progress_controller.update_work_context(
            task_id="task123",
            files_read=["config.py", "main.py"],
            files_modified=["feature.py", "test.py"],
            key_decisions=["Use async pattern", "Add caching"],
            discoveries=["Found performance issue"],
            test_results={"unit": "passed", "integration": "passed"}
        )
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="update_work_context",
            task_id="task123",
            files_read=["config.py", "main.py"],
            files_modified=["feature.py", "test.py"],
            key_decisions=["Use async pattern", "Add caching"],
            discoveries=["Found performance issue"],
            test_results={"unit": "passed", "integration": "passed"}
        )
        
        assert result["success"] is True

    def test_update_work_context_minimal_parameters(self, progress_controller, mock_operation_factory):
        """Test update_work_context with minimal parameters."""
        result = progress_controller.update_work_context(task_id="task123")
        
        mock_operation_factory.handle_operation.assert_called_once_with(
            operation="update_work_context",
            task_id="task123",
            files_read=None,
            files_modified=None,
            key_decisions=None,
            discoveries=None,
            test_results=None
        )

    def test_update_work_context_partial_parameters(self, progress_controller, mock_operation_factory):
        """Test update_work_context with some parameters."""
        result = progress_controller.update_work_context(
            task_id="task123",
            files_read=["README.md"],
            discoveries=["Need to refactor module X"]
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["files_read"] == ["README.md"]
        assert call_kwargs["files_modified"] is None
        assert call_kwargs["key_decisions"] is None
        assert call_kwargs["discoveries"] == ["Need to refactor module X"]
        assert call_kwargs["test_results"] is None


class TestFactoryIntegration:
    """Test integration with operation factory."""

    def test_factory_success_response_propagation(self, progress_controller, mock_operation_factory):
        """Test that factory success responses are propagated correctly."""
        mock_operation_factory.handle_operation.return_value = {
            "success": True,
            "data": {"progress_type": "testing", "percentage": 80},
            "message": "Progress reported successfully"
        }
        
        result = progress_controller.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Running tests",
            percentage=80
        )
        
        assert result == mock_operation_factory.handle_operation.return_value

    def test_factory_error_response_propagation(self, progress_controller, mock_operation_factory):
        """Test that factory error responses are propagated correctly."""
        mock_operation_factory.handle_operation.return_value = {
            "success": False,
            "error": "Invalid percentage: 150",
            "error_code": "VALIDATION_ERROR"
        }
        
        result = progress_controller.report_progress(
            task_id="task123",
            progress_type="testing",
            description="Testing",
            percentage=150
        )
        
        assert result["success"] is False
        assert "Invalid percentage" in result["error"]

    def test_factory_exception_handling(self, progress_controller, mock_operation_factory):
        """Test handling when factory raises exception."""
        mock_operation_factory.handle_operation.side_effect = Exception("Factory error")
        
        with pytest.raises(Exception, match="Factory error"):
            progress_controller.report_progress(
                task_id="task123",
                progress_type="debugging",
                description="Debugging"
            )


class TestModularArchitecture:
    """Test modular architecture components."""

    def test_response_formatter_initialization(self, mock_task_facade, mock_context_facade_factory):
        """Test that StandardResponseFormatter is initialized."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter') as mock_formatter_class, \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory'):
            
            controller = ProgressToolsController(
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            mock_formatter_class.assert_called_once()

    def test_operation_factory_initialization(self, mock_task_facade, mock_context_facade_factory):
        """Test that ProgressOperationFactory is initialized with correct parameters."""
        with patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.StandardResponseFormatter') as mock_formatter_class, \
             patch('fastmcp.task_management.interface.mcp_controllers.progress_tools_controller.progress_tools_controller.ProgressOperationFactory') as mock_factory_class:
            
            mock_formatter = Mock()
            mock_formatter_class.return_value = mock_formatter
            
            controller = ProgressToolsController(
                task_facade=mock_task_facade,
                context_facade_factory=mock_context_facade_factory
            )
            
            mock_factory_class.assert_called_once_with(
                mock_formatter,
                mock_task_facade,
                mock_context_facade_factory
            )


class TestMethodChaining:
    """Test method calls can be chained."""

    def test_multiple_method_calls(self, progress_controller, mock_operation_factory):
        """Test multiple method calls work independently."""
        mock_operation_factory.handle_operation.side_effect = [
            {"success": True, "message": "Progress reported"},
            {"success": True, "message": "Task updated"},
            {"success": True, "message": "Checkpoint created"}
        ]
        
        # Call multiple methods
        result1 = progress_controller.report_progress(
            task_id="task1",
            progress_type="implementation",
            description="Working"
        )
        
        result2 = progress_controller.quick_task_update(
            task_id="task2",
            status="in_progress"
        )
        
        result3 = progress_controller.checkpoint_work(
            task_id="task3",
            current_state="Testing",
            next_steps=["Deploy"]
        )
        
        # Verify all calls were made
        assert mock_operation_factory.handle_operation.call_count == 3
        assert result1["message"] == "Progress reported"
        assert result2["message"] == "Task updated"
        assert result3["message"] == "Checkpoint created"


class TestParameterPassing:
    """Test parameter passing to factory."""

    def test_none_parameters_preserved(self, progress_controller, mock_operation_factory):
        """Test that None parameters are preserved when passed to factory."""
        progress_controller.quick_task_update(
            task_id="task123",
            status=None,
            notes="Some notes",
            completed_work=None
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["status"] is None
        assert call_kwargs["notes"] == "Some notes"
        assert call_kwargs["completed_work"] is None

    def test_empty_lists_preserved(self, progress_controller, mock_operation_factory):
        """Test that empty lists are preserved when passed to factory."""
        progress_controller.report_progress(
            task_id="task123",
            progress_type="planning",
            description="Planning",
            files_affected=[],
            next_steps=[]
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["files_affected"] == []
        assert call_kwargs["next_steps"] == []

    def test_complex_data_structures(self, progress_controller, mock_operation_factory):
        """Test that complex data structures are passed correctly."""
        test_results = {
            "unit": {"passed": 10, "failed": 0},
            "integration": {"passed": 5, "failed": 1},
            "coverage": 85.5
        }
        
        progress_controller.update_work_context(
            task_id="task123",
            test_results=test_results
        )
        
        call_kwargs = mock_operation_factory.handle_operation.call_args[1]
        assert call_kwargs["test_results"] == test_results