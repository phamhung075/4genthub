"""Unit tests for Email value object"""

import pytest
from fastmcp.auth.domain.value_objects.email import Email


class TestEmail:
    """Tests for Email value object"""
    
    def test_create_valid_email(self):
        """Test creating an Email with a valid email address"""
        email = Email("user@example.com")
        assert email.value == "user@example.com"
    
    def test_email_normalization(self):
        """Test that email addresses are normalized to lowercase"""
        email = Email("User@EXAMPLE.COM")
        assert email.value == "user@example.com"
        
        # Test with whitespace
        email2 = Email("  user@example.com  ")
        assert email2.value == "user@example.com"
    
    def test_from_string_factory(self):
        """Test creating Email using from_string factory method"""
        email = Email.from_string("user@example.com")
        assert email.value == "user@example.com"
    
    def test_get_domain(self):
        """Test extracting domain part from email"""
        email = Email("user@example.com")
        assert email.get_domain() == "example.com"
        
        email2 = Email("admin@subdomain.example.org")
        assert email2.get_domain() == "subdomain.example.org"
    
    def test_get_local_part(self):
        """Test extracting local part from email"""
        email = Email("user@example.com")
        assert email.get_local_part() == "user"
        
        email2 = Email("john.doe+tag@example.com")
        assert email2.get_local_part() == "john.doe+tag"
    
    def test_string_representation(self):
        """Test string representation of Email"""
        email = Email("user@example.com")
        assert str(email) == "user@example.com"
    
    def test_equality(self):
        """Test Email equality comparison"""
        email1 = Email("user@example.com")
        email2 = Email("user@example.com")
        email3 = Email("USER@EXAMPLE.COM")  # Should be equal after normalization
        email4 = Email("other@example.com")
        
        assert email1 == email2
        assert email1 == email3
        assert email1 != email4
        assert email1 != "user@example.com"  # Not equal to string
    
    def test_hashable(self):
        """Test that Email can be used in sets and as dict keys"""
        email1 = Email("user@example.com")
        email2 = Email("user@example.com")
        email3 = Email("other@example.com")
        
        # Test in set
        email_set = {email1, email2, email3}
        assert len(email_set) == 2  # email1 and email2 are the same
        
        # Test as dict key
        email_dict = {email1: "value1", email3: "value2"}
        assert email_dict[email2] == "value1"  # email2 should map to same as email1
    
    def test_invalid_email_empty(self):
        """Test that empty email raises ValueError"""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            Email("")
        
        with pytest.raises(ValueError, match="Email cannot be empty"):
            Email(None)
    
    def test_invalid_email_format(self):
        """Test that invalid email formats raise ValueError"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example",
            "user@.com",
            "user..name@example.com",
            "user@example..com",
        ]
        
        for invalid_email in invalid_emails:
            with pytest.raises(ValueError) as exc_info:
                Email(invalid_email)
            # Verify that the error message mentions it's an invalid format
            assert "Invalid email format" in str(exc_info.value) or "Email" in str(exc_info.value)
    
    def test_email_too_long(self):
        """Test that emails exceeding max length raise ValueError"""
        # Create an email that's too long (>254 characters)
        # 254 character limit - need email longer than this
        local_part = "a" * 245  # 245 characters
        domain = "example.com"  # 11 characters, + 1 for @
        long_email = f"{local_part}@{domain}"  # Total: 257 characters
        
        with pytest.raises(ValueError, match="Email address too long"):
            Email(long_email)
    
    def test_valid_complex_emails(self):
        """Test various valid complex email formats"""
        valid_emails = [
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com",
            "123@example.com",
            "a@b.co",
            "test.email.with+symbol@example4u.net",
        ]
        
        for valid_email in valid_emails:
            email = Email(valid_email)
            assert email.value == valid_email.lower()
    
    def test_immutability(self):
        """Test that Email value object is immutable"""
        email = Email("user@example.com")
        
        # Should not be able to modify the value
        with pytest.raises(AttributeError):
            email.value = "other@example.com"