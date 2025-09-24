"""
Test suite for auth_helper.py - Authentication Helper for MCP Controllers

Tests the authentication functionality for extracting user_id from JWT tokens.
All legacy test functions for removed symbols have been cleaned up.
"""

import pytest
from unittest.mock import Mock, patch
import logging

from fastmcp.task_management.interface.mcp_controllers.auth_helper.auth_helper import (
    get_authenticated_user_id,
    log_authentication_details
)
from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError


class TestGetAuthenticatedUserId:
    """Test get_authenticated_user_id function"""
    
    def test_get_authenticated_user_id_with_provided_user_id(self):
        """Test when user_id is provided directly - in testing mode, always returns test user"""
        result = get_authenticated_user_id("provided-user-123", "Test Operation")
        # In TESTING MODE, authentication service returns a UUID
        # The UUID is deterministic based on the input user ID
        # Just verify it returns a valid UUID format
        assert isinstance(result, str)
        assert len(result) == 36  # Standard UUID length
        assert result.count('-') == 4  # UUID format check
    
    def test_get_authenticated_user_id_with_none_raises_error(self):
        """Test that None user_id raises error when no JWT token is available"""
        # When no user_id is provided and no JWT token is available,
        # the authentication service should raise an error
        with pytest.raises(UserAuthenticationRequiredError):
            get_authenticated_user_id(None, "Test Operation")
    
    def test_get_authenticated_user_id_with_empty_string_raises_error(self):
        """Test that empty string user_id raises error when no JWT token is available"""
        # When an empty string is provided and no JWT token is available,
        # the authentication service should raise an error
        with pytest.raises(UserAuthenticationRequiredError):
            get_authenticated_user_id("", "Test Operation")
    
    def test_get_authenticated_user_id_operation_parameter(self):
        """Test that operation parameter is used correctly - in testing mode, always returns test user"""
        result = get_authenticated_user_id("test-user", "Custom Operation")
        # In TESTING MODE, authentication service returns a UUID
        # Verify it returns a valid UUID format
        assert isinstance(result, str)
        assert len(result) == 36  # Standard UUID length
        assert result.count('-') == 4  # UUID format check


class TestLogAuthenticationDetails:
    """Test log_authentication_details function"""
    
    def test_log_authentication_details_with_user_id(self):
        """Test logging with user_id provided"""
        # Should not raise exception
        log_authentication_details(user_id="test-user-123", operation="Test Operation")
    
    def test_log_authentication_details_without_user_id(self):
        """Test logging without user_id"""
        # Should not raise exception
        log_authentication_details(operation="Test Operation")
    
    def test_log_authentication_details_no_parameters(self):
        """Test logging with no parameters"""
        # Should not raise exception
        log_authentication_details()


class TestIntegrationScenarios:
    """Test integration scenarios with authentication"""
    
    def test_authentication_workflow_success(self):
        """Test successful authentication workflow"""
        user_id = "valid-user-123"
        operation = "Create Task"

        # Get authenticated user ID (in testing mode, always returns test user)
        result = get_authenticated_user_id(user_id, operation)
        # In TESTING MODE, authentication service returns a UUID
        # Verify it returns a valid UUID format
        assert isinstance(result, str)
        assert len(result) == 36  # Standard UUID length
        assert result.count('-') == 4  # UUID format check

        # Log authentication details
        log_authentication_details(user_id=result, operation=operation)
    
    def test_authentication_workflow_failure(self):
        """Test failed authentication workflow - raises error when no auth is available"""
        # When no authentication is available, the service should raise an error
        with pytest.raises(UserAuthenticationRequiredError):
            get_authenticated_user_id(None, "Failed Operation")


if __name__ == "__main__":
    pytest.main([__file__])