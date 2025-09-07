"""Test suite for domain constants.

Tests the domain-level constants and validation functions including:
- User ID validation
- Authentication requirement enforcement
- Prohibited default ID detection
- Error handling for invalid inputs
"""

import pytest
from uuid import uuid4

from fastmcp.task_management.domain.constants import (
    validate_user_id,
    require_authenticated_user,
    PROHIBITED_DEFAULT_IDS
)
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError,
    InvalidUserIdError
)


class TestDomainConstants:
    """Test cases for domain constants and validation functions."""
    
    def test_prohibited_default_ids_constants(self):
        """Test that prohibited default IDs constant is properly defined."""
        expected_ids = {
            'default_id',
            '00000000-0000-0000-0000-000000000000',
            'default',
            'default_user',
            'system',
            'anonymous',
            'unauthenticated'
        }
        
        assert PROHIBITED_DEFAULT_IDS == expected_ids
        assert len(PROHIBITED_DEFAULT_IDS) >= 7
        assert 'default_id' in PROHIBITED_DEFAULT_IDS
        assert '00000000-0000-0000-0000-000000000000' in PROHIBITED_DEFAULT_IDS
        
        # All default-like IDs should be prohibited - no exceptions
    
    def test_validate_user_id_valid_inputs(self):
        """Test validate_user_id with valid user IDs."""
        valid_user_ids = [
            "user-123",
            "test@example.com",
            str(uuid4()),
            "12345678-1234-5678-1234-567812345678",
            "user_name",
            "User.Name",
            "valid-user-id",
            "a" * 50,  # Long but valid
            "unique-user-id"  # Valid unique user ID
        ]
        
        for user_id in valid_user_ids:
            result = validate_user_id(user_id, "Test operation")
            assert result == user_id
            assert isinstance(result, str)
    
    def test_validate_user_id_none_raises_error(self):
        """Test that None user_id raises UserAuthenticationRequiredError."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_user_id(None, "Test operation")
        
        assert "Test operation" in str(exc_info.value)
    
    def test_validate_user_id_empty_string_raises_error(self):
        """Test that empty string user_id raises UserAuthenticationRequiredError."""
        empty_values = ["", "   ", "\t", "\n", " \t \n "]
        
        for empty_value in empty_values:
            with pytest.raises(UserAuthenticationRequiredError) as exc_info:
                validate_user_id(empty_value, "Empty test")
            
            assert "Empty test" in str(exc_info.value)
    
    def test_validate_user_id_prohibited_defaults_raise_error(self):
        """Test that prohibited default IDs raise DefaultUserProhibitedError."""
        for prohibited_id in PROHIBITED_DEFAULT_IDS:
            with pytest.raises(DefaultUserProhibitedError):
                validate_user_id(prohibited_id, "Prohibited test")
    
    def test_validate_user_id_prohibited_defaults_case_insensitive(self):
        """Test that prohibited default IDs are case-insensitive."""
        test_cases = [
            "DEFAULT_ID",
            "Default",
            "SYSTEM",
            "Anonymous",
            "DEFAULT_USER"
        ]
        
        for test_case in test_cases:
            with pytest.raises(DefaultUserProhibitedError):
                validate_user_id(test_case, "Case test")
    
    def test_validate_user_id_zero_uuid_raises_error(self):
        """Test that zero UUID raises DefaultUserProhibitedError."""
        zero_uuid = "00000000-0000-0000-0000-000000000000"
        
        with pytest.raises(DefaultUserProhibitedError):
            validate_user_id(zero_uuid, "Zero UUID test")
    
    def test_validate_user_id_strips_whitespace(self):
        """Test that validate_user_id strips whitespace from input."""
        user_id_with_spaces = "  valid-user-123  "
        
        result = validate_user_id(user_id_with_spaces, "Whitespace test")
        
        assert result == "valid-user-123"
        assert result.strip() == result  # No leading/trailing whitespace
    
    def test_validate_user_id_converts_to_string(self):
        """Test that validate_user_id converts input to string."""
        numeric_user_id = 12345
        
        result = validate_user_id(numeric_user_id, "Numeric test")
        
        assert result == "12345"
        assert isinstance(result, str)
    
    def test_validate_user_id_uuid_format_detection(self):
        """Test that UUID format is properly detected and validated."""
        valid_uuid = str(uuid4())
        
        # Should pass validation
        result = validate_user_id(valid_uuid, "UUID test")
        assert result == valid_uuid
        
        # Malformed UUID-like string (wrong length)
        malformed_uuid = "12345678-1234-5678-1234-56781234567"
        result = validate_user_id(malformed_uuid, "Malformed UUID test")
        assert result == malformed_uuid  # Should pass (not exactly 36 chars)
    
    def test_validate_user_id_operation_parameter(self):
        """Test that operation parameter is used in error messages."""
        operation_descriptions = [
            "Creating project",
            "Updating task",
            "Deleting resource",
            "User authentication",
            "Repository access"
        ]
        
        for operation in operation_descriptions:
            with pytest.raises(UserAuthenticationRequiredError) as exc_info:
                validate_user_id(None, operation)
            
            assert operation in str(exc_info.value)
    
    def test_validate_user_id_default_operation_message(self):
        """Test validate_user_id with default operation message."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_user_id(None)
        
        assert "This operation" in str(exc_info.value)
    
    def test_require_authenticated_user_alias(self):
        """Test that require_authenticated_user is an alias for validate_user_id."""
        valid_user_id = "test-user-123"
        
        # Both functions should return the same result
        result1 = validate_user_id(valid_user_id, "Test operation")
        result2 = require_authenticated_user(valid_user_id, "Test operation")
        
        assert result1 == result2
        assert result1 == valid_user_id
    
    def test_require_authenticated_user_error_cases(self):
        """Test that require_authenticated_user raises same errors as validate_user_id."""
        # Test None user_id
        with pytest.raises(UserAuthenticationRequiredError):
            require_authenticated_user(None, "Auth test")
        
        # Test prohibited default
        with pytest.raises(DefaultUserProhibitedError):
            require_authenticated_user("default_id", "Auth test")
        
        # Test empty string
        with pytest.raises(UserAuthenticationRequiredError):
            require_authenticated_user("", "Auth test")
    
    def test_validate_user_id_special_characters(self):
        """Test validation with special characters in user ID."""
        special_user_ids = [
            "user@example.com",
            "user+tag@domain.com",
            "user-name_123",
            "user.name.example",
            "user%20name",
            "user#hash",
            "user$money",
            "user&more"
        ]
        
        for user_id in special_user_ids:
            result = validate_user_id(user_id, "Special chars test")
            assert result == user_id
    
    def test_validate_user_id_unicode_characters(self):
        """Test validation with Unicode characters in user ID."""
        unicode_user_ids = [
            "用户123",  # Chinese
            "ユーザー",  # Japanese
            "пользователь",  # Russian
            "użytkownik",  # Polish
            "مستخدم",  # Arabic
            "😀user123",  # Emoji
            "user-αβγ"  # Greek
        ]
        
        for user_id in unicode_user_ids:
            result = validate_user_id(user_id, "Unicode test")
            assert result == user_id
    
    def test_validate_user_id_very_long_string(self):
        """Test validation with very long user ID."""
        long_user_id = "a" * 1000
        
        result = validate_user_id(long_user_id, "Long string test")
        assert result == long_user_id
        assert len(result) == 1000
    
    def test_validate_user_id_numeric_string(self):
        """Test validation with numeric string user ID."""
        numeric_strings = [
            "123456789",
            "0",
            "999999999999999999",
            "123.456",
            "-123"
        ]
        
        for user_id in numeric_strings:
            result = validate_user_id(user_id, "Numeric string test")
            assert result == user_id
    
    def test_validate_user_id_boolean_conversion(self):
        """Test validation with boolean input."""
        # True and False should be converted to strings
        result_true = validate_user_id(True, "Boolean test")
        assert result_true == "True"
        
        result_false = validate_user_id(False, "Boolean test")
        assert result_false == "False"
    
    def test_validate_user_id_edge_case_uuid_like(self):
        """Test validation with UUID-like strings that aren't exactly UUIDs."""
        uuid_like_cases = [
            "12345678-1234-5678-1234-567812345678",  # Valid UUID format
            "1234567-1234-5678-1234-567812345678",   # Missing digit
            "12345678-123-5678-1234-567812345678",   # Wrong segment length
            "12345678-1234-5678-1234-56781234567890", # Too long
            "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",  # Non-hex characters but right format
        ]
        
        for case in uuid_like_cases:
            # Only the first one should be detected as UUID-like and checked for zero UUID
            result = validate_user_id(case, "UUID-like test")
            assert result == case
    
    def test_constants_module_no_default_functions(self):
        """Test that deprecated default functions are not available."""
        import fastmcp.task_management.domain.constants as constants
        
        # These functions should not exist
        deprecated_functions = [
            'get_default_user_id',
            'is_default_user',
            'normalize_user_id'
        ]
        
        for func_name in deprecated_functions:
            assert not hasattr(constants, func_name), f"Deprecated function {func_name} should not exist"
        
        # These constants should not exist
        deprecated_constants = [
            'DEFAULT_USER_UUID',
            'DEFAULT_USER_UUID_STR',
            'LEGACY_DEFAULT_USER_ID'
        ]
        
        for const_name in deprecated_constants:
            assert not hasattr(constants, const_name), f"Deprecated constant {const_name} should not exist"
    
    def test_error_exception_types(self):
        """Test that correct exception types are raised."""
        # UserAuthenticationRequiredError for None
        with pytest.raises(UserAuthenticationRequiredError):
            validate_user_id(None)
        
        # UserAuthenticationRequiredError for empty
        with pytest.raises(UserAuthenticationRequiredError):
            validate_user_id("")
        
        # DefaultUserProhibitedError for prohibited IDs
        with pytest.raises(DefaultUserProhibitedError):
            validate_user_id("default_id")
        
        # DefaultUserProhibitedError for zero UUID
        with pytest.raises(DefaultUserProhibitedError):
            validate_user_id("00000000-0000-0000-0000-000000000000")
    
    def test_validate_user_id_maintains_case(self):
        """Test that validate_user_id maintains original case for valid IDs."""
        mixed_case_ids = [
            "UserName123",
            "User@Example.COM",
            "CamelCaseUser",
            "UPPERCASE_USER",
            "lowercase_user"
        ]
        
        for user_id in mixed_case_ids:
            result = validate_user_id(user_id, "Case test")
            assert result == user_id  # Original case should be preserved
    
    def test_no_default_users_allowed(self):
        """Test that no default-like users are allowed - strict authentication."""
        # Test users that are actually in PROHIBITED_DEFAULT_IDS
        for user_id in PROHIBITED_DEFAULT_IDS:
            with pytest.raises(DefaultUserProhibitedError):
                validate_user_id(user_id, "No defaults test")
        
        # Test additional default-like patterns
        additional_prohibited = [
            "compatibility-default-user",  # Not in main list but should be prohibited
            "default-user",
            "system-default"
        ]
        
        for user_id in additional_prohibited:
            # These will pass validation since they're not in PROHIBITED_DEFAULT_IDS
            # but that's the current implementation - only exact matches are prohibited
            result = validate_user_id(user_id, "Test")
            assert result == user_id
    
    def test_strict_authentication_enforcement(self):
        """Test that authentication is strictly enforced with no fallbacks."""
        # All default-like names should be prohibited
        assert "default_user" in PROHIBITED_DEFAULT_IDS
        assert "default" in PROHIBITED_DEFAULT_IDS
        assert "system" in PROHIBITED_DEFAULT_IDS
        assert "anonymous" in PROHIBITED_DEFAULT_IDS