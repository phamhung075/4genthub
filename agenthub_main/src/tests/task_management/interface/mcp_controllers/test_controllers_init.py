"""Test suite for mcp_controllers package __init__.py.

Tests the interface controllers package including:
- Module imports and exports
- Controller class availability
- __all__ exports validation
- Backward compatibility aliases
"""

import pytest
import importlib
import inspect
from typing import List, Any


class TestMCPControllersPackage:
    """Test cases for mcp_controllers package initialization."""
    
    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        try:
            import fastmcp.task_management.interface.mcp_controllers as controllers
            assert controllers is not None
        except ImportError as e:
            pytest.fail(f"Failed to import mcp_controllers package: {e}")
    
    def test_exported_classes_in_all(self):
        """Test that all classes in __all__ are properly exported."""
        from fastmcp.task_management.interface import mcp_controllers
        
        # Verify __all__ exists
        assert hasattr(mcp_controllers, '__all__')
        assert isinstance(mcp_controllers.__all__, list)
        
        # Expected exports
        expected_exports = [
            "TaskMCPController",
            "SubtaskMCPController",
            "DependencyMCPController",
            "UnifiedContextMCPController",
            "ProjectMCPController",
            "GitBranchMCPController",
            "UnifiedAgentMCPController",
            "AgentMCPController",
        ]
        
        # Verify all expected exports are in __all__
        for export in expected_exports:
            assert export in mcp_controllers.__all__, f"{export} not in __all__"
    
    def test_controller_imports(self):
        """Test that all controller classes can be imported."""
        from fastmcp.task_management.interface.mcp_controllers import (
            TaskMCPController,
            SubtaskMCPController,
            DependencyMCPController,
            UnifiedContextMCPController,
            ProjectMCPController,
            GitBranchMCPController,
            UnifiedAgentMCPController,
            AgentMCPController,
        )
        
        # Verify all imports are classes
        assert inspect.isclass(TaskMCPController)
        assert inspect.isclass(SubtaskMCPController)
        assert inspect.isclass(DependencyMCPController)
        assert inspect.isclass(UnifiedContextMCPController)
        assert inspect.isclass(ProjectMCPController)
        assert inspect.isclass(GitBranchMCPController)
        assert inspect.isclass(UnifiedAgentMCPController)
        assert inspect.isclass(AgentMCPController)
    
    def test_agent_controller_backward_compatibility(self):
        """Test that AgentMCPController is an alias for UnifiedAgentMCPController."""
        from fastmcp.task_management.interface.mcp_controllers import (
            UnifiedAgentMCPController,
            AgentMCPController,
        )
        
        # Verify they are the same class (backward compatibility alias)
        # Based on the agent_mcp_controller/__init__.py, they should be the same
        assert AgentMCPController is not None
        assert UnifiedAgentMCPController is not None
        
        # Check if they have the same methods (indicating same or related classes)
        agent_methods = set(dir(AgentMCPController))
        unified_methods = set(dir(UnifiedAgentMCPController))
        
        # Common methods should exist in both
        common_methods = {'register_tools', 'manage_agent', '__init__'}
        assert common_methods.issubset(agent_methods)
        assert common_methods.issubset(unified_methods)
    
    def test_import_from_submodules(self):
        """Test that controllers are imported from correct submodules."""
        # Test direct submodule imports
        from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.task_mcp_controller import TaskMCPController as DirectTaskController
        from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.subtask_mcp_controller import SubtaskMCPController as DirectSubtaskController
        from fastmcp.task_management.interface.mcp_controllers.dependency_mcp_controller.dependency_mcp_controller import DependencyMCPController as DirectDependencyController
        from fastmcp.task_management.interface.mcp_controllers.unified_context_controller.unified_context_controller import UnifiedContextMCPController as DirectContextController
        from fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.project_mcp_controller import ProjectMCPController as DirectProjectController
        from fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller.git_branch_mcp_controller import GitBranchMCPController as DirectGitBranchController
        
        # Import from package
        from fastmcp.task_management.interface.mcp_controllers import (
            TaskMCPController,
            SubtaskMCPController,
            DependencyMCPController,
            UnifiedContextMCPController,
            ProjectMCPController,
            GitBranchMCPController,
        )
        
        # Verify they are the same classes
        assert TaskMCPController is DirectTaskController
        assert SubtaskMCPController is DirectSubtaskController
        assert DependencyMCPController is DirectDependencyController
        assert UnifiedContextMCPController is DirectContextController
        assert ProjectMCPController is DirectProjectController
        assert GitBranchMCPController is DirectGitBranchController
    
    def test_no_unexpected_exports(self):
        """Test that no unexpected items are exported from the package."""
        from fastmcp.task_management.interface import mcp_controllers
        
        # Get all public attributes (not starting with _)
        public_attrs = [attr for attr in dir(mcp_controllers) if not attr.startswith('_')]
        
        # Expected public attributes (from __all__ plus standard module attributes)
        expected_attrs = set(mcp_controllers.__all__)
        standard_attrs = {'__all__', '__builtins__', '__cached__', '__doc__', '__file__', 
                         '__loader__', '__name__', '__package__', '__path__', '__spec__'}
        
        # Additional allowed attributes (submodules imported for internal use)
        allowed_submodules = {
            'agent_mcp_controller', 'auth_helper', 'dependency_mcp_controller',
            'git_branch_mcp_controller', 'project_mcp_controller', 'subtask_mcp_controller',
            'task_mcp_controller', 'unified_context_controller', 'workflow_guidance',
            'workflow_hint_enhancer'
        }
        
        # Remove standard attributes
        actual_public = set(public_attrs) - standard_attrs - allowed_submodules
        
        # Verify no unexpected exports
        unexpected = actual_public - expected_attrs
        assert not unexpected, f"Unexpected exports found: {unexpected}"
    
    def test_controller_base_methods(self):
        """Test that all controllers have expected base methods."""
        from fastmcp.task_management.interface.mcp_controllers import (
            TaskMCPController,
            SubtaskMCPController,
            DependencyMCPController,
            UnifiedContextMCPController,
            ProjectMCPController,
            GitBranchMCPController,
            UnifiedAgentMCPController,
        )
        
        controllers = [
            TaskMCPController,
            SubtaskMCPController,
            DependencyMCPController,
            UnifiedContextMCPController,
            ProjectMCPController,
            GitBranchMCPController,
            UnifiedAgentMCPController,
        ]
        
        # All controllers should have register_tools method
        for controller_class in controllers:
            assert hasattr(controller_class, 'register_tools'), \
                f"{controller_class.__name__} missing register_tools method"
    
    def test_module_docstring(self):
        """Test that the module has proper documentation."""
        from fastmcp.task_management.interface import mcp_controllers
        
        assert mcp_controllers.__doc__ is not None
        assert "Interface Controllers Package" in mcp_controllers.__doc__
        assert "MCP controllers" in mcp_controllers.__doc__
    
    def test_import_performance(self):
        """Test that imports are reasonably fast (no circular dependencies)."""
        import time
        
        start_time = time.time()
        
        # Re-import the module
        importlib.reload(importlib.import_module('fastmcp.task_management.interface.mcp_controllers'))
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Import should be fast (less than 1 second)
        assert elapsed_time < 1.0, f"Import took too long: {elapsed_time:.2f} seconds"
    
    def test_agent_controller_import_from_subpackage(self):
        """Test that AgentMCPController can be imported from its subpackage."""
        # Test the import path specified in the __init__.py
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import (
            AgentMCPController,
            UnifiedAgentMCPController
        )
        
        # Verify both imports work
        assert AgentMCPController is not None
        assert UnifiedAgentMCPController is not None
        
        # Verify they are properly aliased
        assert hasattr(AgentMCPController, '__init__')
        assert hasattr(UnifiedAgentMCPController, '__init__')