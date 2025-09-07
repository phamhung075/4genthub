"""Test suite for authentication exceptions.

Tests the authentication-related exception classes including:
- Base AuthenticationError
- UserAuthenticationRequiredError
- InvalidUserIdError  
- DefaultUserProhibitedError
- Exception message formatting
- Exception inheritance
"""

import pytest

from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    AuthenticationError,
    UserAuthenticationRequiredError,
    InvalidUserIdError,
    DefaultUserProhibitedError
)


class TestAuthenticationExceptions:
    """Test cases for authentication exception classes."""
    
    def test_authentication_error_base_class(self):
        """Test AuthenticationError base exception class."""
        # Test basic instantiation
        error = AuthenticationError("Test authentication error")
        
        assert isinstance(error, Exception)
        assert str(error) == "Test authentication error"
        
        # Test with no message
        error_no_msg = AuthenticationError()
        assert isinstance(error_no_msg, Exception)
    
    def test_user_authentication_required_error_default_message(self):
        """Test UserAuthenticationRequiredError with default operation."""
        error = UserAuthenticationRequiredError()
        
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, Exception)
        assert "This operation" in str(error)
        assert "requires user authentication" in str(error)
        assert "No user ID was provided" in str(error)
        assert error.operation == "This operation"
    
    def test_user_authentication_required_error_custom_operation(self):
        """Test UserAuthenticationRequiredError with custom operation description."""
        operation = "Creating a new project"
        error = UserAuthenticationRequiredError(operation)
        
        assert isinstance(error, AuthenticationError)
        assert operation in str(error)
        assert "requires user authentication" in str(error)
        assert "No user ID was provided" in str(error)
        assert error.operation == operation
    
    def test_user_authentication_required_error_various_operations(self):
        """Test UserAuthenticationRequiredError with various operation descriptions."""
        operations = [
            "Project creation",
            "Task management",
            "Repository access",
            "User profile update",
            "File upload operation",
            "Database query execution",
            "API endpoint access"
        ]
        
        for operation in operations:
            error = UserAuthenticationRequiredError(operation)
            
            assert isinstance(error, AuthenticationError)
            assert operation in str(error)
            assert error.operation == operation
            assert "requires user authentication" in str(error)
    
    def test_invalid_user_id_error(self):
        """Test InvalidUserIdError with various invalid user IDs."""
        invalid_user_ids = [
            "invalid-uuid",
            "",
            "   ",
            "malformed@id",
            "123-456-789",
            "user with spaces",
            "null",
            "undefined"
        ]
        
        for invalid_id in invalid_user_ids:
            error = InvalidUserIdError(invalid_id)
            
            assert isinstance(error, AuthenticationError)
            assert isinstance(error, Exception)
            assert invalid_id in str(error)
            assert "Invalid user ID provided" in str(error)
            assert "User authentication is required" in str(error)
            assert error.user_id == invalid_id
    
    def test_invalid_user_id_error_special_characters(self):
        """Test InvalidUserIdError with special characters."""
        special_ids = [
            "user@domain.com",
            "user#123",
            "user$money",
            "user%20encoded",
            "user&more",
            "user*wildcard",
            "user+plus",
            "user=equals"
        ]
        
        for special_id in special_ids:
            error = InvalidUserIdError(special_id)
            
            assert isinstance(error, AuthenticationError)
            assert special_id in str(error)
            assert error.user_id == special_id
    
    def test_invalid_user_id_error_unicode(self):
        """Test InvalidUserIdError with Unicode characters."""
        unicode_ids = [
            "用户123",  # Chinese
            "ユーザー",  # Japanese
            "пользователь",  # Russian
            "😀user",  # Emoji
            "user-αβγ"  # Greek
        ]
        
        for unicode_id in unicode_ids:
            error = InvalidUserIdError(unicode_id)
            
            assert isinstance(error, AuthenticationError)
            assert unicode_id in str(error)
            assert error.user_id == unicode_id
    
    def test_default_user_prohibited_error(self):
        """Test DefaultUserProhibitedError."""
        error = DefaultUserProhibitedError()
        
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, Exception)
        assert "Use of default user ID is prohibited" in str(error)
        assert "authenticated user credentials" in str(error)
        assert "All operations must be performed" in str(error)
    
    def test_default_user_prohibited_error_no_parameters(self):
        """Test that DefaultUserProhibitedError takes no parameters."""
        # Should work with no parameters
        error = DefaultUserProhibitedError()
        assert isinstance(error, AuthenticationError)
        
        # Message should be consistent
        error1 = DefaultUserProhibitedError()
        error2 = DefaultUserProhibitedError()
        assert str(error1) == str(error2)
    
    def test_exception_inheritance_hierarchy(self):
        """Test the inheritance hierarchy of authentication exceptions."""
        # Test that all exceptions inherit from AuthenticationError
        user_auth_error = UserAuthenticationRequiredError("test")
        invalid_id_error = InvalidUserIdError("test")
        default_prohibited_error = DefaultUserProhibitedError()
        
        assert isinstance(user_auth_error, AuthenticationError)
        assert isinstance(invalid_id_error, AuthenticationError)
        assert isinstance(default_prohibited_error, AuthenticationError)
        
        # Test that AuthenticationError inherits from Exception
        assert isinstance(AuthenticationError(), Exception)
        
        # Test that all inherit from Exception
        assert isinstance(user_auth_error, Exception)
        assert isinstance(invalid_id_error, Exception)
        assert isinstance(default_prohibited_error, Exception)
    
    def test_exception_attributes(self):
        """Test that exceptions have expected attributes."""
        # UserAuthenticationRequiredError should have operation attribute
        operation = "Test operation"
        user_error = UserAuthenticationRequiredError(operation)
        assert hasattr(user_error, 'operation')
        assert user_error.operation == operation
        
        # InvalidUserIdError should have user_id attribute
        user_id = "invalid-id"
        invalid_error = InvalidUserIdError(user_id)
        assert hasattr(invalid_error, 'user_id')
        assert invalid_error.user_id == user_id
        
        # DefaultUserProhibitedError should not have specific attributes
        default_error = DefaultUserProhibitedError()
        # Should not have operation or user_id attributes
        assert not hasattr(default_error, 'operation')
        assert not hasattr(default_error, 'user_id')
    
    def test_exception_message_completeness(self):
        """Test that exception messages contain all expected information."""
        # UserAuthenticationRequiredError message components
        user_error = UserAuthenticationRequiredError("Project creation")
        message = str(user_error)
        assert "Project creation" in message
        assert "requires user authentication" in message
        assert "No user ID was provided" in message
        
        # InvalidUserIdError message components
        invalid_error = InvalidUserIdError("bad-id")
        message = str(invalid_error)
        assert "Invalid user ID provided" in message
        assert "bad-id" in message
        assert "User authentication is required" in message
        
        # DefaultUserProhibitedError message components
        default_error = DefaultUserProhibitedError()
        message = str(default_error)
        assert "Use of default user ID is prohibited" in message
        assert "All operations must be performed" in message
        assert "authenticated user credentials" in message
    
    def test_exception_can_be_raised_and_caught(self):
        """Test that exceptions can be properly raised and caught."""
        # Test UserAuthenticationRequiredError
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            raise UserAuthenticationRequiredError("test operation")
        
        assert "test operation" in str(exc_info.value)
        assert exc_info.value.operation == "test operation"
        
        # Test InvalidUserIdError
        with pytest.raises(InvalidUserIdError) as exc_info:
            raise InvalidUserIdError("bad-id")
        
        assert "bad-id" in str(exc_info.value)
        assert exc_info.value.user_id == "bad-id"
        
        # Test DefaultUserProhibitedError
        with pytest.raises(DefaultUserProhibitedError) as exc_info:
            raise DefaultUserProhibitedError()
        
        assert "prohibited" in str(exc_info.value)
    
    def test_exception_can_be_caught_as_base_class(self):
        """Test that specific exceptions can be caught as AuthenticationError."""
        # UserAuthenticationRequiredError as AuthenticationError
        with pytest.raises(AuthenticationError):
            raise UserAuthenticationRequiredError("test")
        
        # InvalidUserIdError as AuthenticationError
        with pytest.raises(AuthenticationError):
            raise InvalidUserIdError("test")
        
        # DefaultUserProhibitedError as AuthenticationError
        with pytest.raises(AuthenticationError):
            raise DefaultUserProhibitedError()
    
    def test_exception_can_be_caught_as_exception(self):
        """Test that all exceptions can be caught as general Exception."""
        # UserAuthenticationRequiredError as Exception
        with pytest.raises(Exception):
            raise UserAuthenticationRequiredError("test")
        
        # InvalidUserIdError as Exception
        with pytest.raises(Exception):
            raise InvalidUserIdError("test")
        
        # DefaultUserProhibitedError as Exception
        with pytest.raises(Exception):
            raise DefaultUserProhibitedError()
        
        # AuthenticationError as Exception
        with pytest.raises(Exception):
            raise AuthenticationError("test")
    
    def test_exception_string_representation(self):
        """Test string representation of exceptions."""
        # Test __str__ method
        user_error = UserAuthenticationRequiredError("custom operation")
        assert isinstance(str(user_error), str)
        assert len(str(user_error)) > 0
        
        invalid_error = InvalidUserIdError("invalid-123")
        assert isinstance(str(invalid_error), str)
        assert len(str(invalid_error)) > 0
        
        default_error = DefaultUserProhibitedError()
        assert isinstance(str(default_error), str)
        assert len(str(default_error)) > 0
        
        # Test __repr__ method should work
        assert isinstance(repr(user_error), str)
        assert isinstance(repr(invalid_error), str)
        assert isinstance(repr(default_error), str)
    
    def test_exception_empty_or_none_inputs(self):
        """Test exception behavior with empty or None inputs."""
        # UserAuthenticationRequiredError with empty operation
        empty_op_error = UserAuthenticationRequiredError("")
        assert str(empty_op_error)  # Should not crash
        assert empty_op_error.operation == ""
        
        # InvalidUserIdError with empty user_id
        empty_id_error = InvalidUserIdError("")
        assert str(empty_id_error)  # Should not crash
        assert empty_id_error.user_id == ""
        
        # InvalidUserIdError with None (converted to string)
        none_id_error = InvalidUserIdError(None)
        assert str(none_id_error)  # Should not crash
        assert none_id_error.user_id is None
    
    def test_exception_message_immutability(self):
        """Test that exception messages are consistent."""
        # Same operation should produce same message
        error1 = UserAuthenticationRequiredError("test op")
        error2 = UserAuthenticationRequiredError("test op")
        assert str(error1) == str(error2)
        
        # Same user_id should produce same message
        error1 = InvalidUserIdError("test-id")
        error2 = InvalidUserIdError("test-id")
        assert str(error1) == str(error2)
        
        # DefaultUserProhibitedError should always have same message
        error1 = DefaultUserProhibitedError()
        error2 = DefaultUserProhibitedError()
        assert str(error1) == str(error2)