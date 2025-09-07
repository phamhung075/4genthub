"""Test suite for AuthConfig module.

Tests authentication configuration including:
- Default user permissions
- Environment variable handling
- Fallback user ID generation
- Security enforcement
- Migration readiness validation
"""

import os
import pytest
import logging
from unittest.mock import patch, MagicMock
from fastmcp.config.auth_config import AuthConfig
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError
)


class TestAuthConfig:
    """Test cases for AuthConfig class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Store original environment variables
        self.original_env = os.environ.copy()
        # Clear relevant environment variables
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        os.environ.pop('ENVIRONMENT', None)
    
    def teardown_method(self):
        """Clean up after tests."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_should_enforce_authentication_always_true(self):
        """Test that authentication is always enforced."""
        assert AuthConfig.should_enforce_authentication() is True
    
    def test_validate_security_requirements_no_legacy_issues(self):
        """Test security validation with no legacy configuration issues."""
        # Clear any legacy environment variables
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        os.environ['ENVIRONMENT'] = 'production'
        
        result = AuthConfig.validate_security_requirements()
        
        assert result['authentication_required'] is True
        assert len(result['legacy_config_issues']) == 0
        assert result['secure'] is True
        assert result['environment'] == 'production'
    
    def test_validate_security_requirements_with_legacy_issues(self):
        """Test security validation with legacy configuration issues."""
        # Set legacy environment variable that bypasses security
        os.environ['ALLOW_DEFAULT_USER'] = 'true'
        os.environ['ENVIRONMENT'] = 'production'
        
        result = AuthConfig.validate_security_requirements()
        
        assert result['authentication_required'] is True
        assert len(result['legacy_config_issues']) == 1
        assert "ALLOW_DEFAULT_USER environment variable is set" in result['legacy_config_issues']
        assert result['secure'] is False
        assert result['environment'] == 'production'
    
    def test_validate_security_requirements_unknown_environment(self):
        """Test security validation with unknown environment."""
        # Clear environment variable
        os.environ.pop('ENVIRONMENT', None)
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        
        result = AuthConfig.validate_security_requirements()
        
        assert result['authentication_required'] is True
        assert len(result['legacy_config_issues']) == 0
        assert result['secure'] is True
        assert result['environment'] == 'unknown'
    
    def test_validate_security_requirements_multiple_environment_formats(self):
        """Test security validation with different environment formats."""
        environments = ['production', 'prod', 'PRODUCTION', 'staging', 'test', 'development', 'dev']
        
        for env in environments:
            os.environ['ENVIRONMENT'] = env
            os.environ.pop('ALLOW_DEFAULT_USER', None)
            
            result = AuthConfig.validate_security_requirements()
            
            assert result['authentication_required'] is True
            assert result['environment'] == env.lower()
            assert len(result['legacy_config_issues']) == 0
            assert result['secure'] is True
    
    def test_auth_config_strict_enforcement(self):
        """Test that AuthConfig always enforces strict authentication."""
        # Authentication should always be required regardless of environment variables
        os.environ['ALLOW_DEFAULT_USER'] = 'true'
        os.environ['ENVIRONMENT'] = 'development'
        
        # Authentication is always enforced
        assert AuthConfig.should_enforce_authentication() is True
        
        # Remove legacy variables and test again
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        os.environ['ENVIRONMENT'] = 'production'
        
        assert AuthConfig.should_enforce_authentication() is True
    
    def test_security_requirements_consistency(self):
        """Test consistency between security requirements and enforcement."""
        # Test with no legacy issues
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        os.environ['ENVIRONMENT'] = 'production'
        
        security_result = AuthConfig.validate_security_requirements()
        enforcement = AuthConfig.should_enforce_authentication()
        
        assert security_result['authentication_required'] is True
        assert enforcement is True
        assert security_result['secure'] is True
        
        # Test with legacy issues
        os.environ['ALLOW_DEFAULT_USER'] = 'true'
        
        security_result = AuthConfig.validate_security_requirements()
        enforcement = AuthConfig.should_enforce_authentication()
        
        # Authentication still required but security compromised by legacy config
        assert security_result['authentication_required'] is True
        assert enforcement is True  # Always enforced
        assert security_result['secure'] is False  # But security is compromised
    
    def test_security_requirements_edge_cases(self):
        """Test edge cases in security requirements validation."""
        # Test with empty environment variable
        os.environ['ENVIRONMENT'] = ''
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        
        result = AuthConfig.validate_security_requirements()
        
        assert result['authentication_required'] is True
        assert result['environment'] == 'unknown'  # Empty string becomes 'unknown'
        assert result['secure'] is True
        
        # Test with whitespace-only environment
        os.environ['ENVIRONMENT'] = '   '
        
        result = AuthConfig.validate_security_requirements()
        
        assert result['environment'] == 'unknown'  # Whitespace stripped becomes empty, then 'unknown'
    
    def test_thread_safety_auth_config(self):
        """Test thread safety of AuthConfig methods."""
        import threading
        import time
        
        # Set a stable environment for thread safety test
        os.environ['ENVIRONMENT'] = 'production'
        os.environ.pop('ALLOW_DEFAULT_USER', None)
        
        results = []
        errors = []
        
        def check_config():
            try:
                # Each thread does multiple operations
                for _ in range(10):
                    should_enforce = AuthConfig.should_enforce_authentication()
                    security_validation = AuthConfig.validate_security_requirements()
                    
                    # Results should be consistent
                    assert should_enforce is True  # Always enforced
                    assert security_validation['authentication_required'] is True
                    
                    results.append((should_enforce, security_validation['secure']))
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=check_config)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check no errors occurred
        assert len(errors) == 0, f"Thread errors occurred: {errors}"
        
        # All results should be consistent
        if results:
            first_result = results[0]
            for result in results:
                assert result == first_result, "Inconsistent results across threads"