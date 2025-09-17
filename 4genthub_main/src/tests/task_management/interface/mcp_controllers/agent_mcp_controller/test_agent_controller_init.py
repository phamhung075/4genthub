"""Test suite for agent_mcp_controller package __init__.py.

Tests the unified agent MCP controller package including:
- Module imports and exports
- Controller class availability
- Backward compatibility aliases
- Package structure validation
"""

import pytest
import importlib
import inspect
from typing import Any


class TestAgentMCPControllerPackage:
    """Test cases for agent_mcp_controller package initialization."""
    
    def test_module_imports(self):
        """Test that the module can be imported successfully."""
        try:
            import fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller as agent_controller
            assert agent_controller is not None
        except ImportError as e:
            pytest.fail(f"Failed to import agent_mcp_controller package: {e}")
    
    def test_exported_classes_in_all(self):
        """Test that all classes in __all__ are properly exported."""
        from fastmcp.task_management.interface.mcp_controllers import agent_mcp_controller
        
        # Verify __all__ exists
        assert hasattr(agent_mcp_controller, '__all__')
        assert isinstance(agent_mcp_controller.__all__, list)
        
        # Expected exports based on __init__.py
        expected_exports = [
            "UnifiedAgentMCPController",
            "AgentMCPController",
        ]
        
        # Verify all expected exports are in __all__
        for export in expected_exports:
            assert export in agent_mcp_controller.__all__, f"{export} not in __all__"
        
        # Verify __all__ contains exactly these exports
        assert set(agent_mcp_controller.__all__) == set(expected_exports)
    
    def test_controller_imports(self):
        """Test that controller classes can be imported."""
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import (
            AgentMCPController,
            UnifiedAgentMCPController,
        )
        
        # Verify imports are not None
        assert AgentMCPController is not None
        assert UnifiedAgentMCPController is not None
        
        # Verify they are classes (or at least callable)
        assert callable(AgentMCPController)
        assert callable(UnifiedAgentMCPController)
    
    def test_backward_compatibility_alias(self):
        """Test that UnifiedAgentMCPController is an alias for AgentMCPController."""
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import (
            AgentMCPController,
            UnifiedAgentMCPController,
        )
        
        # Based on the __init__.py, UnifiedAgentMCPController should be an alias
        # UnifiedAgentMCPController = AgentMCPController
        assert UnifiedAgentMCPController is AgentMCPController
        
        # They should be the exact same object
        assert id(UnifiedAgentMCPController) == id(AgentMCPController)
    
    def test_import_from_submodule(self):
        """Test that AgentMCPController is imported from the correct submodule."""
        # Import directly from the submodule
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller.agent_mcp_controller import (
            AgentMCPController as DirectAgentController
        )
        
        # Import from package
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import AgentMCPController
        
        # Verify they are the same class
        assert AgentMCPController is DirectAgentController
    
    def test_module_docstring(self):
        """Test that the module has proper documentation."""
        from fastmcp.task_management.interface.mcp_controllers import agent_mcp_controller
        
        assert agent_mcp_controller.__doc__ is not None
        assert "Unified Agent MCP Controller" in agent_mcp_controller.__doc__
        assert "Complete Operations Package" in agent_mcp_controller.__doc__
        assert "agent management" in agent_mcp_controller.__doc__
        assert "agent invocation" in agent_mcp_controller.__doc__
    
    def test_no_unexpected_exports(self):
        """Test that no unexpected items are exported from the package."""
        from fastmcp.task_management.interface.mcp_controllers import agent_mcp_controller
        
        # Get all public attributes (not starting with _)
        public_attrs = [attr for attr in dir(agent_mcp_controller) if not attr.startswith('_')]
        
        # Expected public attributes (from __all__ plus standard module attributes)
        expected_attrs = set(agent_mcp_controller.__all__)
        standard_attrs = {'__all__', '__builtins__', '__cached__', '__doc__', '__file__', 
                         '__loader__', '__name__', '__package__', '__path__', '__spec__'}
        
        # Additional allowed attributes (submodules imported for internal use)
        allowed_submodules = {
            'agent_mcp_controller', 'factories', 'handlers', 'manage_agent_description'
        }
        
        # Remove standard attributes and allowed submodules
        actual_public = set(public_attrs) - standard_attrs - allowed_submodules
        
        # Verify no unexpected exports
        unexpected = actual_public - expected_attrs
        assert not unexpected, f"Unexpected exports found: {unexpected}"
    
    def test_controller_has_expected_methods(self):
        """Test that AgentMCPController has expected methods."""
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import AgentMCPController
        
        # Expected methods for an MCP controller
        expected_methods = [
            '__init__',
            'register_tools',
            'manage_agent',
        ]
        
        # Verify methods exist
        for method in expected_methods:
            assert hasattr(AgentMCPController, method), \
                f"AgentMCPController missing {method} method"
    
    def test_import_performance(self):
        """Test that imports are reasonably fast (no circular dependencies)."""
        import time
        
        start_time = time.time()
        
        # Re-import the module
        module_name = 'fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller'
        importlib.reload(importlib.import_module(module_name))
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Import should be fast (less than 0.5 seconds)
        assert elapsed_time < 0.5, f"Import took too long: {elapsed_time:.2f} seconds"
    
    def test_package_structure(self):
        """Test that the package has expected structure."""
        from fastmcp.task_management.interface.mcp_controllers import agent_mcp_controller
        
        # Package should have __path__ attribute
        assert hasattr(agent_mcp_controller, '__path__')
        
        # Package should be a proper package (not just a module)
        assert hasattr(agent_mcp_controller, '__package__')
        
        # Package name should be correct
        expected_package = 'fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller'
        assert agent_mcp_controller.__package__ == expected_package
    
    def test_unified_controller_functionality_preserved(self):
        """Test that unified functionality is preserved through aliasing."""
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import (
            AgentMCPController,
            UnifiedAgentMCPController,
        )
        
        # Create mock facade service for testing
        mock_facade_service = type('MockFacadeService', (), {
            'get_agent_facade': lambda self, **kwargs: None
        })()
        
        # Both should be instantiable with the same parameters
        # Note: We're not actually instantiating to avoid dependencies
        # Just verify they are the same class
        assert AgentMCPController == UnifiedAgentMCPController
        
        # Verify class name
        assert AgentMCPController.__name__ == "AgentMCPController"
        
        # Since UnifiedAgentMCPController is an alias, it should have the same __name__
        assert UnifiedAgentMCPController.__name__ == "AgentMCPController"
    
    def test_import_from_parent_package(self):
        """Test that controllers can be imported from parent package."""
        # Test that the agent controller can be imported from the parent mcp_controllers package
        from fastmcp.task_management.interface.mcp_controllers import (
            AgentMCPController as ParentAgentController,
            UnifiedAgentMCPController as ParentUnifiedController,
        )
        
        # Import from this package
        from fastmcp.task_management.interface.mcp_controllers.agent_mcp_controller import (
            AgentMCPController,
            UnifiedAgentMCPController,
        )
        
        # They should be the same objects
        assert ParentAgentController is AgentMCPController
        assert ParentUnifiedController is UnifiedAgentMCPController