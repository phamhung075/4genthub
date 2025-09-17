"""
Tests for auth middleware package imports and exports
"""

import pytest
from unittest.mock import patch, MagicMock


class TestMiddlewarePackageImports:
    """Test suite for middleware package imports"""

    def test_imports_jwt_auth_middleware(self):
        """Test that JWT auth middleware components are imported"""
        from fastmcp.auth.middleware import (
            JWTAuthMiddleware,
            UserContextManager
        )
        
        assert JWTAuthMiddleware is not None
        assert UserContextManager is not None

    def test_imports_dual_auth_middleware(self):
        """Test that dual auth middleware components are imported"""
        from fastmcp.auth.middleware import (
            DualAuthMiddleware,
            create_dual_auth_middleware
        )
        
        assert DualAuthMiddleware is not None
        assert create_dual_auth_middleware is not None

    def test_imports_request_context_middleware(self):
        """Test that request context middleware components are imported"""
        from fastmcp.auth.middleware import (
            RequestContextMiddleware,
            create_request_context_middleware,
            get_current_user_id,
            get_current_user_email,
            get_current_auth_method,
            is_request_authenticated,
            get_authentication_context
        )
        
        assert RequestContextMiddleware is not None
        assert create_request_context_middleware is not None
        assert get_current_user_id is not None
        assert get_current_user_email is not None
        assert get_current_auth_method is not None
        assert is_request_authenticated is not None
        assert get_authentication_context is not None

    def test_all_exports(self):
        """Test __all__ exports the expected names"""
        from fastmcp.auth import middleware
        
        expected_exports = [
            "JWTAuthMiddleware",
            "UserContextManager",
            "DualAuthMiddleware",
            "create_dual_auth_middleware",
            "RequestContextMiddleware",
            "create_request_context_middleware",
            "get_current_user_id",
            "get_current_user_email",
            "get_current_auth_method",
            "is_request_authenticated",
            "get_authentication_context"
        ]
        
        assert set(middleware.__all__) == set(expected_exports)
        
        # Verify all exported names exist in module
        for export in expected_exports:
            assert hasattr(middleware, export), f"Missing export: {export}"

    def test_module_structure(self):
        """Test the module can be imported and has expected structure"""
        import fastmcp.auth.middleware as middleware
        
        # Check module attributes
        assert hasattr(middleware, '__all__')
        assert isinstance(middleware.__all__, list)
        
        # Check all exported names exist in module
        for name in middleware.__all__:
            assert hasattr(middleware, name), f"Export {name} not found in module"

    def test_import_backward_compatibility(self):
        """Test imports for backward compatibility"""
        # Test that commonly used imports still work
        try:
            from fastmcp.auth.middleware import JWTAuthMiddleware
            assert JWTAuthMiddleware is not None
        except ImportError:
            pytest.fail("Failed to import JWTAuthMiddleware")

        try:
            from fastmcp.auth.middleware import RequestContextMiddleware
            assert RequestContextMiddleware is not None
        except ImportError:
            pytest.fail("Failed to import RequestContextMiddleware")

    def test_function_imports(self):
        """Test that helper functions can be imported"""
        from fastmcp.auth import middleware
        
        # Test context helper functions
        assert callable(middleware.get_current_user_id)
        assert callable(middleware.get_current_user_email)
        assert callable(middleware.get_current_auth_method)
        assert callable(middleware.is_request_authenticated)
        assert callable(middleware.get_authentication_context)
        
        # Test factory functions
        assert callable(middleware.create_dual_auth_middleware)
        assert callable(middleware.create_request_context_middleware)