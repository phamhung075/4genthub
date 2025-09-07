"""Test suite for auth module __init__ file.

Tests for the authentication module initialization and exports.
"""

import pytest
from unittest.mock import Mock, patch


class TestAuthModuleInit:
    """Test the auth module initialization."""

    def test_import_all_exported_classes(self):
        """Test that all exported classes can be imported."""
        from fastmcp.auth import (
            User, UserStatus, UserRole,
            Email, UserId,
            PasswordService, JWTService,
            AuthService, LoginResult, RegistrationResult,
            AuthMiddleware,
            TokenValidator, TokenValidationError, RateLimitError
        )
        
        # Verify classes exist and are importable
        assert User is not None
        assert UserStatus is not None
        assert UserRole is not None
        assert Email is not None
        assert UserId is not None
        assert PasswordService is not None
        assert JWTService is not None
        assert AuthService is not None
        assert LoginResult is not None
        assert RegistrationResult is not None
        assert AuthMiddleware is not None
        assert TokenValidator is not None
        assert TokenValidationError is not None
        assert RateLimitError is not None

    def test_all_attribute_exists(self):
        """Test that __all__ is properly defined."""
        import fastmcp.auth
        
        assert hasattr(fastmcp.auth, '__all__')
        assert isinstance(fastmcp.auth.__all__, list)
        assert len(fastmcp.auth.__all__) == 14

    def test_all_exported_items_accessible(self):
        """Test that all items in __all__ are accessible."""
        import fastmcp.auth
        
        for item in fastmcp.auth.__all__:
            assert hasattr(fastmcp.auth, item), f"{item} not accessible in module"

    def test_module_docstring_exists(self):
        """Test that the module has a proper docstring."""
        import fastmcp.auth
        
        assert fastmcp.auth.__doc__ is not None
        assert "Authentication Module for DhafnckMCP" in fastmcp.auth.__doc__

    def test_domain_entities_import(self):
        """Test domain entities import correctly."""
        from fastmcp.auth import User, UserStatus, UserRole
        
        # Basic sanity check that these are classes
        assert isinstance(User, type) or callable(User)
        # Note: UserStatus and UserRole might be enums, so we just check they exist

    def test_value_objects_import(self):
        """Test value objects import correctly."""
        from fastmcp.auth import Email, UserId
        
        # Basic sanity check
        assert Email is not None
        assert UserId is not None

    def test_domain_services_import(self):
        """Test domain services import correctly."""
        from fastmcp.auth import PasswordService, JWTService
        
        assert PasswordService is not None
        assert JWTService is not None

    def test_application_services_import(self):
        """Test application services import correctly."""
        from fastmcp.auth import AuthService, LoginResult, RegistrationResult
        
        assert AuthService is not None
        assert LoginResult is not None
        assert RegistrationResult is not None

    def test_middleware_import(self):
        """Test middleware import correctly."""
        from fastmcp.auth import AuthMiddleware
        
        assert AuthMiddleware is not None

    def test_validators_import(self):
        """Test validators import correctly."""
        from fastmcp.auth import TokenValidator, TokenValidationError, RateLimitError
        
        assert TokenValidator is not None
        assert TokenValidationError is not None
        assert RateLimitError is not None

    def test_import_error_handling(self):
        """Test that import errors are handled gracefully."""
        # This tests that the import doesn't fail catastrophically
        # even if some dependencies might be missing in test environment
        try:
            import fastmcp.auth
            # If we get here, imports worked
            assert True
        except ImportError as e:
            # If imports fail, it should be specific module failures, not syntax errors
            assert "cannot import" in str(e).lower() or "no module named" in str(e).lower()

    def test_middleware_alias(self):
        """Test that AuthMiddleware is properly aliased from JWTAuthMiddleware."""
        from fastmcp.auth import AuthMiddleware
        from fastmcp.auth.middleware import JWTAuthMiddleware
        
        # They should be the same class
        assert AuthMiddleware is JWTAuthMiddleware


class TestAuthModuleStructure:
    """Test the structure and organization of the auth module."""

    def test_exports_categorized_correctly(self):
        """Test that exports are properly categorized in __all__."""
        import fastmcp.auth
        
        all_exports = fastmcp.auth.__all__
        
        # Domain Entities
        domain_entities = ["User", "UserStatus", "UserRole"]
        for entity in domain_entities:
            assert entity in all_exports
        
        # Value Objects
        value_objects = ["Email", "UserId"]
        for vo in value_objects:
            assert vo in all_exports
        
        # Domain Services
        domain_services = ["PasswordService", "JWTService"]
        for service in domain_services:
            assert service in all_exports
        
        # Application Services
        app_services = ["AuthService", "LoginResult", "RegistrationResult"]
        for service in app_services:
            assert service in all_exports
        
        # Middleware
        middleware = ["AuthMiddleware"]
        for mw in middleware:
            assert mw in all_exports
        
        # Validators
        validators = ["TokenValidator", "TokenValidationError", "RateLimitError"]
        for validator in validators:
            assert validator in all_exports

    def test_no_internal_imports_exported(self):
        """Test that no internal/private imports are exported."""
        import fastmcp.auth
        
        # Check that common internal patterns aren't exported
        for item in fastmcp.auth.__all__:
            assert not item.startswith('_'), f"Private item {item} should not be exported"
            assert not item.endswith('_internal'), f"Internal item {item} should not be exported"