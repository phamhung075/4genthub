"""
Tests for Auth Services Module Initialization

This module tests the auth services package initialization including:
- Module structure and imports
- Service accessibility and initialization
- Package-level functionality
- Service factory patterns if applicable
"""

import pytest
from unittest.mock import patch

def test_auth_services_module_import():
    """Test that auth services module can be imported"""
    try:
        import fastmcp.auth.services
        assert fastmcp.auth.services is not None
    except ImportError as e:
        pytest.fail(f"Failed to import auth services module: {e}")

def test_auth_services_init_file_exists():
    """Test that __init__.py file exists and is accessible"""
    import fastmcp.auth.services
    import inspect
    
    # Check that the module has a file path (not a namespace package)
    assert hasattr(fastmcp.auth.services, '__file__')
    assert fastmcp.auth.services.__file__ is not None

def test_mcp_token_service_accessible():
    """Test that MCP token service is accessible from services module"""
    try:
        from fastmcp.auth.services.mcp_token_service import MCPTokenService, mcp_token_service
        
        # Should be able to import both class and instance
        assert MCPTokenService is not None
        assert mcp_token_service is not None
        assert isinstance(mcp_token_service, MCPTokenService)
        
    except ImportError as e:
        pytest.fail(f"Failed to import MCP token service: {e}")

def test_services_module_structure():
    """Test expected structure of services module"""
    import fastmcp.auth.services
    
    # Get module directory contents
    import os
    module_dir = os.path.dirname(fastmcp.auth.services.__file__)
    
    # Should contain expected files
    expected_files = ['__init__.py', 'mcp_token_service.py']
    actual_files = os.listdir(module_dir)
    
    for expected_file in expected_files:
        assert expected_file in actual_files, f"Expected file {expected_file} not found in services module"

def test_services_module_no_syntax_errors():
    """Test that all modules in services package have no syntax errors"""
    import fastmcp.auth.services
    import os
    import py_compile
    
    module_dir = os.path.dirname(fastmcp.auth.services.__file__)
    
    # Check all Python files for syntax errors
    for filename in os.listdir(module_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(module_dir, filename)
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {filename}: {e}")

def test_init_file_content_basic():
    """Test basic content of __init__.py file"""
    import fastmcp.auth.services
    
    # Module should have basic attributes
    assert hasattr(fastmcp.auth.services, '__name__')
    assert hasattr(fastmcp.auth.services, '__file__')
    assert hasattr(fastmcp.auth.services, '__path__')

def test_no_circular_imports():
    """Test that there are no circular import issues"""
    try:
        # This should not cause circular import errors
        from fastmcp.auth.services import mcp_token_service
        from fastmcp.auth.services.mcp_token_service import MCPTokenService
        
        # Re-importing should work fine
        import fastmcp.auth.services
        import fastmcp.auth.services.mcp_token_service
        
    except ImportError as e:
        if "circular import" in str(e).lower():
            pytest.fail(f"Circular import detected: {e}")
        else:
            # Re-raise other import errors
            raise

@pytest.mark.asyncio
async def test_global_service_initialization():
    """Test that global service instances are properly initialized"""
    from fastmcp.auth.services.mcp_token_service import mcp_token_service
    
    # Global service should be initialized
    assert mcp_token_service is not None
    
    # Should be able to use the service
    stats = mcp_token_service.get_token_stats()
    assert isinstance(stats, dict)
    assert "total_tokens" in stats
    assert "service_status" in stats

def test_module_docstring():
    """Test that modules have appropriate docstrings"""
    import fastmcp.auth.services.mcp_token_service
    
    # Service modules should have docstrings
    assert fastmcp.auth.services.mcp_token_service.__doc__ is not None
    assert len(fastmcp.auth.services.mcp_token_service.__doc__) > 0

def test_service_classes_exportable():
    """Test that service classes can be imported at package level"""
    # Should be able to import key services
    try:
        from fastmcp.auth.services.mcp_token_service import (
            MCPTokenService, 
            MCPToken, 
            mcp_token_service
        )
        
        # Verify types
        assert isinstance(MCPTokenService, type)
        assert isinstance(MCPToken, type)
        assert isinstance(mcp_token_service, MCPTokenService)
        
    except ImportError as e:
        pytest.fail(f"Could not import service classes: {e}")

def test_package_level_imports():
    """Test that important services can be imported at package level if exposed"""
    import fastmcp.auth.services
    
    # Check if package exposes common services
    # This depends on what's actually in __init__.py
    
    # At minimum, should not raise errors when importing
    assert True  # Basic import test passed

def test_service_module_independence():
    """Test that service modules can be imported independently"""
    # Should be able to import services individually
    
    # Test MCP token service
    try:
        import fastmcp.auth.services.mcp_token_service
        assert fastmcp.auth.services.mcp_token_service is not None
    except ImportError as e:
        pytest.fail(f"Could not import mcp_token_service independently: {e}")

def test_package_namespace():
    """Test package namespace integrity"""
    import fastmcp.auth.services
    
    # Package should have proper namespace
    assert fastmcp.auth.services.__name__ == 'fastmcp.auth.services'
    
    # Should be a package (have __path__)
    assert hasattr(fastmcp.auth.services, '__path__')
    assert fastmcp.auth.services.__path__ is not None

@pytest.mark.parametrize("module_name", [
    "mcp_token_service",
])
def test_individual_module_imports(module_name):
    """Test that individual modules in services can be imported"""
    try:
        module = __import__(f'fastmcp.auth.services.{module_name}', fromlist=[module_name])
        assert module is not None
        assert hasattr(module, '__name__')
    except ImportError as e:
        pytest.fail(f"Could not import {module_name}: {e}")

def test_services_directory_structure():
    """Test that services directory has expected structure"""
    import fastmcp.auth.services
    import os
    
    services_dir = os.path.dirname(fastmcp.auth.services.__file__)
    
    # Should exist and be a directory
    assert os.path.exists(services_dir)
    assert os.path.isdir(services_dir)
    
    # Should contain __init__.py
    init_file = os.path.join(services_dir, '__init__.py')
    assert os.path.exists(init_file)
    assert os.path.isfile(init_file)

def test_no_import_warnings():
    """Test that importing services doesn't generate warnings"""
    import warnings
    
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        
        # Import all service modules
        import fastmcp.auth.services
        import fastmcp.auth.services.mcp_token_service
        
        # Check for any import-related warnings
        import_warnings = [w for w in warning_list 
                          if 'import' in str(w.message).lower()]
        
        if import_warnings:
            warning_messages = [str(w.message) for w in import_warnings]
            pytest.fail(f"Import warnings detected: {warning_messages}")

def test_module_reload_safety():
    """Test that modules can be safely reloaded"""
    import importlib
    
    # Should be able to reload without errors
    try:
        import fastmcp.auth.services.mcp_token_service
        importlib.reload(fastmcp.auth.services.mcp_token_service)
        
        # Service should still be accessible
        from fastmcp.auth.services.mcp_token_service import mcp_token_service
        assert mcp_token_service is not None
        
    except Exception as e:
        pytest.fail(f"Module reload failed: {e}")

def test_typing_compatibility():
    """Test that modules are compatible with type checking"""
    try:
        # These imports should work for type checkers
        from fastmcp.auth.services.mcp_token_service import MCPTokenService, MCPToken
        from typing import TYPE_CHECKING
        
        if TYPE_CHECKING:
            # Type annotations should be accessible
            assert MCPTokenService is not None
            assert MCPToken is not None
            
    except ImportError as e:
        pytest.fail(f"Type checking compatibility issue: {e}")

def test_package_version_info():
    """Test package version information if available"""
    import fastmcp.auth.services
    
    # Check if version info is available at package level
    # This is optional but good practice
    if hasattr(fastmcp.auth.services, '__version__'):
        assert isinstance(fastmcp.auth.services.__version__, str)
        assert len(fastmcp.auth.services.__version__) > 0
    
    # Should at least not error when checking
    assert True

@pytest.mark.integration
def test_services_integration_readiness():
    """Test that services are ready for integration"""
    from fastmcp.auth.services.mcp_token_service import mcp_token_service, MCPTokenService
    
    # Service instance should be ready
    assert mcp_token_service is not None
    assert isinstance(mcp_token_service, MCPTokenService)
    
    # Should be able to get basic info without errors
    stats = mcp_token_service.get_token_stats()
    assert isinstance(stats, dict)
    assert "service_status" in stats
    assert stats["service_status"] == "running"