# Authentication Testing Patterns

## Overview

This guide provides comprehensive patterns for testing authentication in the 4genthub platform following the 2025-08-25 test modernization initiative. All authentication testing now enforces strict security patterns with no default user fallbacks.

## 🔒 Security Requirements

### Mandatory Authentication Testing
- **All Operations**: Must test both authenticated and unauthenticated scenarios
- **No Default Users**: All validation functions require explicit user authentication
- **Error Validation**: Must test `UserAuthenticationRequiredError` scenarios
- **Consistent Mocking**: Use standardized authentication mocking patterns

### Authentication Flow Testing
```python
# Test the complete authentication flow
@patch('module.get_current_user_id')
@patch('module.validate_user_id') 
def test_complete_auth_flow(self, mock_validate, mock_get_user_id):
    """Test complete authentication validation flow."""
    mock_get_user_id.return_value = "jwt-user-123"
    mock_validate.return_value = "jwt-user-123"
    
    result = service.authenticated_operation()
    
    assert result["success"] is True
    mock_get_user_id.assert_called_once()
    mock_validate.assert_called_once_with("jwt-user-123", "operation context")
```

## 🧪 Core Testing Patterns

### 1. Standard Authentication Test Pattern

**For Controller Tests:**
```python
import pytest
from unittest.mock import Mock, patch
from fastmcp.task_management.domain.exceptions.authentication_exceptions import (
    UserAuthenticationRequiredError,
    DefaultUserProhibitedError
)

class TestMyController:
    """Test cases for MyController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_facade_factory = Mock()
        self.mock_facade = Mock()
        self.mock_facade_factory.create_facade.return_value = self.mock_facade
        self.controller = MyController(self.mock_facade_factory)
    
    @patch('module.get_current_user_id')
    def test_operation_with_authentication(self, mock_get_user_id):
        """Test operation with proper authentication."""
        mock_get_user_id.return_value = "authenticated-user-123"
        
        result = self.controller.operation()
        
        assert result["success"] is True
        mock_get_user_id.assert_called_once()
    
    @patch('module.get_current_user_id')
    def test_operation_without_auth_raises_error(self, mock_get_user_id):
        """Test operation without authentication raises error."""
        mock_get_user_id.return_value = None
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            self.controller.operation()
        
        assert "operation context" in str(exc_info.value)
```

### 2. Facade Authentication Pattern

**For Application Facade Tests:**
```python
class TestApplicationFacade:
    """Test cases for ApplicationFacade."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock()
        self.facade = ApplicationFacade(self.mock_repository)
    
    @patch('module.get_authenticated_user_id')
    def test_facade_operation_with_auth(self, mock_get_auth_user):
        """Test facade operation with authenticated user."""
        mock_get_auth_user.return_value = "facade-user-456"
        
        result = self.facade.business_operation()
        
        assert result["success"] is True
        mock_get_auth_user.assert_called_once_with(None, "business operation")
    
    def test_facade_operation_requires_user_id(self):
        """Test facade operation requires user_id parameter."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            self.facade.business_operation()  # No user_id provided
        
        assert "User authentication is required" in str(exc_info.value)
```

### 3. Service Layer Authentication Pattern

**For Domain Service Tests:**
```python
class TestDomainService:
    """Test cases for DomainService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = DomainService()
    
    def test_domain_operation_with_user(self):
        """Test domain operation with explicit user."""
        user_id = "domain-user-789"
        
        result = self.service.domain_operation(user_id=user_id)
        
        assert result["success"] is True
        assert result["user_id"] == user_id
    
    def test_domain_operation_validates_user_id(self):
        """Test domain operation validates user_id."""
        with pytest.raises(ValueError) as exc_info:
            self.service.domain_operation(user_id=None)
        
        assert "User ID is required" in str(exc_info.value)
```

## 🔐 Authentication Helper Patterns

### 1. Authentication Helper Testing
```python
class TestAuthenticationHelpers:
    """Test authentication helper functions."""
    
    @patch('module.get_current_user_id')
    def test_get_authenticated_user_id_success(self, mock_get_user_id):
        """Test successful user ID retrieval."""
        mock_get_user_id.return_value = "helper-user-123"
        
        result = get_authenticated_user_id(None, "test context")
        
        assert result == "helper-user-123"
        mock_get_user_id.assert_called_once()
    
    @patch('module.get_current_user_id')  
    def test_get_authenticated_user_id_no_auth(self, mock_get_user_id):
        """Test user ID retrieval without authentication."""
        mock_get_user_id.return_value = None
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            get_authenticated_user_id(None, "test context")
        
        assert "test context" in str(exc_info.value)
    
    def test_validate_user_id_success(self):
        """Test user ID validation success."""
        result = validate_user_id("valid-user-123", "validation context")
        
        assert result == "valid-user-123"
    
    def test_validate_user_id_none_raises_error(self):
        """Test user ID validation with None raises error."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_user_id(None, "validation context")
        
        assert "validation context" in str(exc_info.value)
    
    def test_validate_user_id_empty_raises_error(self):
        """Test user ID validation with empty string raises error."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_user_id("", "validation context")
        
        assert "validation context" in str(exc_info.value)
```

### 2. JWT Token Validation Testing
```python
class TestJWTValidation:
    """Test JWT token validation patterns."""
    
    @patch('module.jwt.decode')
    def test_jwt_validation_success(self, mock_jwt_decode):
        """Test successful JWT token validation."""
        mock_jwt_decode.return_value = {
            "sub": "jwt-user-123",
            "user_id": "jwt-user-123",
            "exp": 9999999999  # Future timestamp
        }
        
        result = validate_jwt_token("valid.jwt.token")
        
        assert result["user_id"] == "jwt-user-123"
        mock_jwt_decode.assert_called_once()
    
    @patch('module.jwt.decode')
    def test_jwt_validation_expired(self, mock_jwt_decode):
        """Test JWT token validation with expired token."""
        mock_jwt_decode.side_effect = ExpiredSignatureError("Token expired")
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_jwt_token("expired.jwt.token")
        
        assert "Token expired" in str(exc_info.value)
    
    @patch('module.jwt.decode')
    def test_jwt_validation_invalid(self, mock_jwt_decode):
        """Test JWT token validation with invalid token."""
        mock_jwt_decode.side_effect = InvalidTokenError("Invalid token")
        
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            validate_jwt_token("invalid.jwt.token")
        
        assert "Invalid token" in str(exc_info.value)
```

## 🧩 Integration Testing Patterns

### 1. End-to-End Authentication Flow
```python
class TestAuthenticationIntegration:
    """Integration tests for complete authentication flow."""
    
    @patch('module.get_current_user_id')
    @patch('module.validate_user_id')
    def test_complete_workflow(self, mock_validate, mock_get_user_id):
        """Test complete authenticated workflow."""
        mock_get_user_id.return_value = "integration-user-123"
        mock_validate.return_value = "integration-user-123"
        
        # Test complete flow: Authentication → Validation → Business Logic
        result = self.service.complete_workflow()
        
        assert result["success"] is True
        assert result["user_id"] == "integration-user-123"
        mock_get_user_id.assert_called_once()
        mock_validate.assert_called_once_with("integration-user-123", "Complete workflow")
    
    def test_workflow_authentication_failure(self):
        """Test workflow fails without authentication."""
        with pytest.raises(UserAuthenticationRequiredError) as exc_info:
            self.service.complete_workflow()
        
        assert "authentication is required" in str(exc_info.value).lower()
```

### 2. Multi-Layer Authentication Testing
```python
class TestMultiLayerAuthentication:
    """Test authentication across multiple layers."""
    
    @patch('controller_module.get_current_user_id')
    @patch('facade_module.get_authenticated_user_id') 
    def test_controller_to_facade_auth_propagation(self, mock_facade_auth, mock_controller_auth):
        """Test authentication propagates from controller to facade."""
        mock_controller_auth.return_value = "controller-user-123"
        mock_facade_auth.return_value = "controller-user-123"
        
        result = self.controller.operation_that_calls_facade()
        
        assert result["success"] is True
        mock_controller_auth.assert_called_once()
        mock_facade_auth.assert_called_once_with("controller-user-123", "facade operation")
```

## ⚠️ Common Anti-Patterns (Deprecated)

### ❌ What NOT to Do

**1. Default User Patterns (REMOVED):**
```python
# ❌ Never use default user patterns
def test_with_default_user(self):
    result = service.operation(user_id="default")  # Deprecated
    assert result["success"] is True

def test_allows_none_user(self):
    result = service.operation(user_id=None)  # Deprecated  
    assert result["user_id"] == "system_default"  # No longer allowed
```

**2. Compatibility Mode Testing (REMOVED):**
```python
# ❌ Never test compatibility modes
def test_compatibility_mode_allows_default(self):
    result = service.operation()  # No default fallbacks allowed
    assert result["success"] is True  # This pattern is deprecated
```

**3. Incomplete Authentication Mocking:**
```python
# ❌ Incomplete mocking
def test_without_proper_mocking(self):
    # Missing authentication mocking - will fail in modern tests
    result = controller.authenticated_operation()  # Will raise UserAuthenticationRequiredError
```

## ✅ Modern Patterns (Required)

### **1. Complete Authentication Coverage:**
```python
# ✅ Test both success and failure cases
@patch('module.get_current_user_id')
def test_operation_success(self, mock_get_user_id):
    mock_get_user_id.return_value = "user-123"
    result = service.operation()
    assert result["success"] is True

def test_operation_requires_auth(self):
    with pytest.raises(UserAuthenticationRequiredError):
        service.operation()  # No mocking = authentication required
```

### **2. Explicit Context Validation:**
```python
# ✅ Always provide context for authentication errors  
def test_operation_context_in_error(self):
    with pytest.raises(UserAuthenticationRequiredError) as exc_info:
        service.specific_operation()
    
    assert "specific_operation" in str(exc_info.value)  # Context validation
```

### **3. Consistent Mocking Patterns:**
```python
# ✅ Use consistent mock patterns
@patch('module.get_current_user_id')
@patch('module.validate_user_id')
def test_with_validation_chain(self, mock_validate, mock_get_user_id):
    mock_get_user_id.return_value = "raw-user-123" 
    mock_validate.return_value = "validated-user-123"
    
    result = service.operation()
    
    assert result["user_id"] == "validated-user-123"
    mock_validate.assert_called_once_with("raw-user-123", "operation context")
```

## 📋 Testing Checklist

### ✅ Pre-Test Requirements
- [ ] Import `UserAuthenticationRequiredError` from exceptions
- [ ] Set up proper mock decorators for authentication functions
- [ ] Plan both success and failure authentication test cases
- [ ] Identify the authentication context for error messages

### ✅ Test Implementation
- [ ] **Success Case**: Mock `get_current_user_id` with valid user
- [ ] **Failure Case**: Test `UserAuthenticationRequiredError` without mocking
- [ ] **Validation**: Test user ID validation if applicable
- [ ] **Context**: Verify error messages include operation context
- [ ] **Assertions**: Check all authentication calls are made correctly

### ✅ Post-Test Validation
- [ ] **Syntax Check**: `python -m py_compile test_file.py`
- [ ] **Import Validation**: All imports resolve correctly
- [ ] **Coverage**: Both authenticated and unauthenticated paths tested
- [ ] **Documentation**: Test methods have clear docstrings

## 📚 Related Documentation

- [Test Modernization Guide](../testing-qa/test-modernization-guide.md)
- [Authentication System Architecture](../CORE ARCHITECTURE/authentication-system.md)
- [User Isolation Architecture](../architecture/user-isolation-architecture.md)
- [Error Handling and Logging](error-handling-and-logging.md)

## 🏷️ Tags

`authentication` `testing` `security` `patterns` `best-practices` `jwt` `user-validation` `error-handling`

---

*Last Updated: 2025-08-25 - Created following Test Modernization Initiative*
*Status: ✅ Complete - Comprehensive authentication testing patterns documented*