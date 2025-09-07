"""
Test suite for auth_helper.py - Authentication Helper for MCP Controllers

Tests the authentication functionality for extracting user_id from JWT tokens
and various authentication contexts with proper fallback mechanisms.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from fastmcp.task_management.interface.controllers.auth_helper import (
    get_user_id_from_request_state,
    _extract_user_id_from_context_object,
    get_authenticated_user_id,
    log_authentication_details
)

class TestExtractUserIdFromContextObject:
    """Test _extract_user_id_from_context_object function"""
    
    def test_extract_from_none(self):
        """Test extraction when context_obj is None"""
        result = _extract_user_id_from_context_object(None)
        assert result is None
    
    def test_extract_from_string(self):
        """Test extraction when context_obj is already a string"""
        user_id = "user-123"
        result = _extract_user_id_from_context_object(user_id)
        assert result == user_id
    
    def test_extract_from_object_with_user_id_attr(self):
        """Test extraction from object with user_id attribute"""
        mock_obj = Mock()
        mock_obj.user_id = "user-456"
        
        result = _extract_user_id_from_context_object(mock_obj)
        assert result == "user-456"
    
    def test_extract_from_object_with_id_attr_fallback(self):
        """Test extraction from object with id attribute when user_id not available"""
        mock_obj = Mock()
        mock_obj.id = "user-789"
        # Remove user_id attribute to test fallback
        if hasattr(mock_obj, 'user_id'):
            delattr(mock_obj, 'user_id')
        
        result = _extract_user_id_from_context_object(mock_obj)
        assert result == "user-789"
    
    def test_extract_from_dict_like_object(self):
        """Test extraction from dict-like object"""
        dict_obj = {"user_id": "dict-user-123", "other_field": "value"}
        
        result = _extract_user_id_from_context_object(dict_obj)
        assert result == "dict-user-123"
    
    def test_extract_from_object_with_numeric_user_id(self):
        """Test extraction when user_id is numeric (converted to string)"""
        mock_obj = Mock()
        mock_obj.user_id = 12345
        
        result = _extract_user_id_from_context_object(mock_obj)
        assert result == "12345"
    
    def test_extract_from_object_with_numeric_id_fallback(self):
        """Test extraction when id is numeric (converted to string)"""
        mock_obj = Mock()
        mock_obj.id = 67890
        # Remove user_id attribute to test fallback
        if hasattr(mock_obj, 'user_id'):
            delattr(mock_obj, 'user_id')
        
        result = _extract_user_id_from_context_object(mock_obj)
        assert result == "67890"
    
    def test_extract_from_dict_without_user_id(self):
        """Test extraction from dict-like object without user_id key"""
        dict_obj = {"name": "test", "email": "test@example.com"}
        
        result = _extract_user_id_from_context_object(dict_obj)
        assert result is None
    
    def test_extract_from_object_without_relevant_attrs(self):
        """Test extraction from object without user_id or id attributes"""
        mock_obj = Mock()
        mock_obj.name = "test"
        mock_obj.email = "test@example.com"
        # Remove user_id and id attributes
        if hasattr(mock_obj, 'user_id'):
            delattr(mock_obj, 'user_id')
        if hasattr(mock_obj, 'id'):
            delattr(mock_obj, 'id')
        
        result = _extract_user_id_from_context_object(mock_obj)
        assert result is None

class TestGetUserIdFromRequestState:
    """Test get_user_id_from_request_state function"""
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_success(self, mock_current_request):
        """Test successful user_id extraction from request state"""
        # Mock request with state and user_id
        mock_request = Mock()
        mock_request.state = Mock()
        mock_request.state.user_id = "request-user-123"
        mock_current_request.get.return_value = mock_request
        
        result = get_user_id_from_request_state()
        assert result == "request-user-123"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_with_context_object(self, mock_current_request):
        """Test user_id extraction when state contains context object"""
        # Mock request with context object
        mock_request = Mock()
        mock_request.state = Mock()
        mock_context_obj = Mock()
        mock_context_obj.user_id = "context-user-456"
        mock_request.state.user_id = mock_context_obj
        mock_current_request.get.return_value = mock_request
        
        result = get_user_id_from_request_state()
        assert result == "context-user-456"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_no_request(self, mock_current_request):
        """Test when no current request is available"""
        mock_current_request.get.return_value = None
        
        result = get_user_id_from_request_state()
        assert result is None
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_no_state(self, mock_current_request):
        """Test when request has no state"""
        mock_request = Mock()
        # Remove state attribute
        if hasattr(mock_request, 'state'):
            delattr(mock_request, 'state')
        mock_current_request.get.return_value = mock_request
        
        result = get_user_id_from_request_state()
        assert result is None
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_no_user_id_in_state(self, mock_current_request):
        """Test when request state exists but has no user_id"""
        mock_request = Mock()
        mock_request.state = Mock()
        # Remove user_id attribute from state
        if hasattr(mock_request.state, 'user_id'):
            delattr(mock_request.state, 'user_id')
        mock_current_request.get.return_value = mock_request
        
        result = get_user_id_from_request_state()
        assert result is None
    
    def test_get_user_id_import_error(self):
        """Test handling of import error for _current_http_request"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request', 
                   side_effect=ImportError("Module not found")):
            result = get_user_id_from_request_state()
            assert result is None
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request')
    def test_get_user_id_exception_handling(self, mock_current_request):
        """Test exception handling in get_user_id_from_request_state"""
        mock_current_request.get.side_effect = Exception("Request error")
        
        result = get_user_id_from_request_state()
        assert result is None

class TestGetAuthenticatedUserId:
    """Test get_authenticated_user_id function"""
    
    def setup_method(self):
        """Setup test fixtures"""
        # Mock validate_user_id to return the input (successful validation)
        self.validate_user_id_patcher = patch('fastmcp.task_management.interface.controllers.auth_helper.validate_user_id')
        self.mock_validate_user_id = self.validate_user_id_patcher.start()
        self.mock_validate_user_id.side_effect = lambda user_id, operation: user_id
        
        # Disable logging during tests to reduce noise
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.CRITICAL)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        self.validate_user_id_patcher.stop()
        # Reset logging level
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.INFO)
    
    def test_get_authenticated_user_id_with_provided_user_id(self):
        """Test when user_id is provided directly"""
        result = get_authenticated_user_id("provided-user-123", "Test Operation")
        
        assert result == "provided-user-123"
        self.mock_validate_user_id.assert_called_once_with("provided-user-123", "Test Operation")
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    @patch('fastmcp.task_management.interface.controllers.auth_helper.is_request_authenticated')
    def test_get_authenticated_user_id_from_request_context(self, mock_is_authenticated, mock_get_user_context):
        """Test extraction from RequestContextMiddleware"""
        # Mock request context returning user object
        mock_user_obj = Mock()
        mock_user_obj.user_id = "request-context-user-123"
        mock_get_user_context.return_value = mock_user_obj
        mock_is_authenticated.return_value = True
        
        result = get_authenticated_user_id(None, "Test Operation")
        
        assert result == "request-context-user-123"
        mock_get_user_context.assert_called_once()
        self.mock_validate_user_id.assert_called_once_with("request-context-user-123", "Test Operation")
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state')
    def test_get_authenticated_user_id_fallback_to_request_state(self, mock_get_request_state, mock_get_user_context):
        """Test fallback to legacy request state when request context fails"""
        # Request context returns None
        mock_get_user_context.return_value = None
        # Request state returns user_id
        mock_get_request_state.return_value = "request-state-user-456"
        
        result = get_authenticated_user_id(None, "Test Operation")
        
        assert result == "request-state-user-456"
        mock_get_user_context.assert_called_once()
        mock_get_request_state.assert_called_once()
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id')
    def test_get_authenticated_user_id_from_user_context(self, mock_get_current_user_id):
        """Test extraction from custom user context middleware"""
        # Mock user context returning string user_id directly
        mock_get_current_user_id.return_value = "user-context-789"
        
        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state', return_value=None):
            result = get_authenticated_user_id(None, "Test Operation")
        
        assert result == "user-context-789"
        mock_get_current_user_id.assert_called_once()
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state')
    def test_get_authenticated_user_id_from_mcp_context(self, mock_get_request_state):
        """Test extraction from MCP authentication context"""
        mock_get_request_state.return_value = None
        
        # Mock MCP auth context
        with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
            mock_user_context = Mock()
            mock_user_context.user_id = "mcp-user-123"
            mock_auth_context.get.return_value = mock_user_context
            
            result = get_authenticated_user_id(None, "Test Operation")
        
        assert result == "mcp-user-123"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state')
    def test_get_authenticated_user_id_mcp_authenticated_user(self, mock_get_request_state):
        """Test extraction from MCP AuthenticatedUser object"""
        mock_get_request_state.return_value = None
        
        # Mock MCP AuthenticatedUser with access_token
        with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
            with patch('mcp.server.auth.middleware.bearer_auth.AuthenticatedUser') as MockAuthenticatedUser:
                mock_authenticated_user = Mock()
                mock_authenticated_user.access_token = Mock()
                mock_authenticated_user.access_token.client_id = "mcp-client-456"
                
                # Make isinstance return True for AuthenticatedUser
                with patch('builtins.isinstance') as mock_isinstance:
                    mock_isinstance.return_value = True
                    mock_auth_context.get.return_value = mock_authenticated_user
                    
                    result = get_authenticated_user_id(None, "Test Operation")
        
        assert result == "mcp-client-456"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state')
    def test_get_authenticated_user_id_no_authentication_error(self, mock_get_request_state):
        """Test error when no authentication is available"""
        mock_get_request_state.return_value = None
        
        # Mock MCP context to return None
        with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
            mock_auth_context.get.return_value = None
            
            with pytest.raises(Exception):  # UserAuthenticationRequiredError
                get_authenticated_user_id(None, "Test Operation")
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_get_authenticated_user_id_request_context_exception(self, mock_get_user_context):
        """Test handling of exception in request context access"""
        # Mock request context to raise exception
        mock_get_user_context.side_effect = Exception("Context access error")
        
        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state', return_value="fallback-user"):
            result = get_authenticated_user_id(None, "Test Operation")
            
            # Should fallback to request state
            assert result == "fallback-user"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id')
    def test_get_authenticated_user_id_user_context_exception(self, mock_get_current_user_id):
        """Test handling of exception in user context access"""
        mock_get_current_user_id.side_effect = Exception("User context error")
        
        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state', return_value=None):
            with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
                mock_user_context = Mock()
                mock_user_context.user_id = "mcp-fallback-user"
                mock_auth_context.get.return_value = mock_user_context
                
                result = get_authenticated_user_id(None, "Test Operation")
                
                # Should fallback to MCP context
                assert result == "mcp-fallback-user"
    
    def test_get_authenticated_user_id_mcp_import_error(self):
        """Test handling of MCP module import error"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False):
            with patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False):
                with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state', return_value=None):
                    # Mock import error for MCP modules
                    with patch('builtins.__import__', side_effect=ImportError("MCP module not found")):
                        with pytest.raises(Exception):  # UserAuthenticationRequiredError
                            get_authenticated_user_id(None, "Test Operation")
    
    def test_get_authenticated_user_id_validation_error(self):
        """Test handling of user ID validation error"""
        # Mock validate_user_id to raise validation error
        self.mock_validate_user_id.side_effect = Exception("Invalid user ID format")
        
        with pytest.raises(Exception, match="Invalid user ID format"):
            get_authenticated_user_id("invalid-user-id", "Test Operation")

class TestGetAuthenticatedUserIdContextObjectHandling:
    """Test get_authenticated_user_id with various context object types"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validate_user_id_patcher = patch('fastmcp.task_management.interface.controllers.auth_helper.validate_user_id')
        self.mock_validate_user_id = self.validate_user_id_patcher.start()
        self.mock_validate_user_id.side_effect = lambda user_id, operation: user_id
        
        # Disable logging during tests
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.CRITICAL)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        self.validate_user_id_patcher.stop()
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.INFO)
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_context_object_with_user_id_attr(self, mock_get_user_context):
        """Test context object with user_id attribute"""
        mock_context_obj = Mock()
        mock_context_obj.user_id = "context-user-123"
        mock_get_user_context.return_value = mock_context_obj
        
        result = get_authenticated_user_id(None, "Test Operation")
        assert result == "context-user-123"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_context_object_with_id_attr_fallback(self, mock_get_user_context):
        """Test context object with id attribute as fallback"""
        mock_context_obj = Mock()
        mock_context_obj.id = "context-id-456"
        # Remove user_id to test fallback
        if hasattr(mock_context_obj, 'user_id'):
            delattr(mock_context_obj, 'user_id')
        mock_get_user_context.return_value = mock_context_obj
        
        result = get_authenticated_user_id(None, "Test Operation")
        assert result == "context-id-456"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_context_object_string_direct(self, mock_get_user_context):
        """Test context returning user_id as string directly"""
        mock_get_user_context.return_value = "direct-string-user-789"
        
        result = get_authenticated_user_id(None, "Test Operation")
        assert result == "direct-string-user-789"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_context_object_dict_like(self, mock_get_user_context):
        """Test context object that behaves like a dictionary"""
        mock_context_dict = {"user_id": "dict-user-123", "email": "user@example.com"}
        mock_get_user_context.return_value = mock_context_dict
        
        result = get_authenticated_user_id(None, "Test Operation")
        assert result == "dict-user-123"
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    def test_context_object_numeric_user_id(self, mock_get_user_context):
        """Test context object with numeric user_id"""
        mock_context_obj = Mock()
        mock_context_obj.user_id = 12345
        mock_get_user_context.return_value = mock_context_obj
        
        result = get_authenticated_user_id(None, "Test Operation")
        assert result == "12345"

class TestLogAuthenticationDetails:
    """Test log_authentication_details function"""
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id')
    def test_log_authentication_details_with_user_context(self, mock_get_current_user_id):
        """Test logging with user context available"""
        mock_get_current_user_id.return_value = "log-test-user-123"
        
        # Should not raise exception
        log_authentication_details()
        
        mock_get_current_user_id.assert_called_once()
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False)
    def test_log_authentication_details_without_user_context(self):
        """Test logging without user context available"""
        # Should not raise exception even without context
        log_authentication_details()
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id')
    def test_log_authentication_details_with_mcp_context(self, mock_get_current_user_id):
        """Test logging with MCP authentication context"""
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock MCP auth context
        with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
            mock_mcp_context = Mock()
            mock_mcp_context.user_id = "mcp-user-456"
            mock_mcp_context.client_id = "client-789"
            mock_auth_context.get.return_value = mock_mcp_context
            
            log_authentication_details()
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True)
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id')
    def test_log_authentication_details_exception_handling(self, mock_get_current_user_id):
        """Test exception handling in log_authentication_details"""
        mock_get_current_user_id.side_effect = Exception("Context error")
        
        # Should not raise exception even with errors
        log_authentication_details()

class TestModuleImportHandling:
    """Test handling of module import availability"""
    
    def test_request_context_import_failure(self):
        """Test handling when RequestContextMiddleware is not available"""
        # This test verifies that the module handles ImportError gracefully
        # The actual import happens at module load time, so we test the fallback behavior
        
        with patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False):
            # Should not raise exception when request context is unavailable
            result = get_authenticated_user_id("test-user", "Test Operation")
            assert result == "test-user"
    
    def test_user_context_import_failure(self):
        """Test handling when user context middleware is not available"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False):
            # Should not raise exception when user context is unavailable
            result = get_authenticated_user_id("test-user", "Test Operation")
            assert result == "test-user"
    
    def test_starlette_import_failure(self):
        """Test handling when Starlette is not available"""
        # The STARLETTE_AVAILABLE flag is set at import time
        # We test that the code doesn't break when Starlette isn't available
        with patch('fastmcp.task_management.interface.controllers.auth_helper.STARLETTE_AVAILABLE', False):
            result = get_authenticated_user_id("test-user", "Test Operation")
            assert result == "test-user"

class TestIntegrationScenarios:
    """Test integration scenarios with multiple authentication methods"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.validate_user_id_patcher = patch('fastmcp.task_management.interface.controllers.auth_helper.validate_user_id')
        self.mock_validate_user_id = self.validate_user_id_patcher.start()
        self.mock_validate_user_id.side_effect = lambda user_id, operation: user_id
        
        # Disable logging during tests
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.CRITICAL)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        self.validate_user_id_patcher.stop()
        logging.getLogger('fastmcp.task_management.interface.controllers.auth_helper').setLevel(logging.INFO)
    
    def test_authentication_priority_order(self):
        """Test that authentication sources are tried in correct priority order"""
        # Setup all authentication sources but with different priorities
        
        with patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True):
            with patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True):
                with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context') as mock_request_context:
                    with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state') as mock_request_state:
                        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id') as mock_user_context:
                            
                            # All sources return different user IDs
                            mock_request_context.return_value = "request-context-user"
                            mock_request_state.return_value = "request-state-user" 
                            mock_user_context.return_value = "user-context-user"
                            
                            result = get_authenticated_user_id(None, "Priority Test")
                            
                            # Should use RequestContextMiddleware (highest priority)
                            assert result == "request-context-user"
                            mock_request_context.assert_called_once()
                            # Lower priority sources should not be called
                            mock_request_state.assert_not_called()
                            mock_user_context.assert_not_called()
    
    def test_authentication_fallback_chain(self):
        """Test complete fallback chain when higher priority sources fail"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True):
            with patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', True):
                with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context') as mock_request_context:
                    with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state') as mock_request_state:
                        with patch('fastmcp.task_management.interface.controllers.auth_helper.get_current_user_id') as mock_user_context:
                            
                            # Higher priority sources return None/fail
                            mock_request_context.return_value = None
                            mock_request_state.return_value = None
                            mock_user_context.return_value = "fallback-user"
                            
                            result = get_authenticated_user_id(None, "Fallback Test")
                            
                            # Should fall back to user context
                            assert result == "fallback-user"
                            mock_request_context.assert_called_once()
                            mock_request_state.assert_called_once()
                            mock_user_context.assert_called_once()
    
    def test_complete_authentication_failure(self):
        """Test when all authentication sources fail"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', False):
            with patch('fastmcp.task_management.interface.controllers.auth_helper.USER_CONTEXT_AVAILABLE', False):
                with patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_id_from_request_state', return_value=None):
                    # Mock MCP context to also return None
                    with patch('mcp.server.auth.context.auth_context') as mock_auth_context:
                        mock_auth_context.get.return_value = None
                        
                        with pytest.raises(Exception):  # UserAuthenticationRequiredError
                            get_authenticated_user_id(None, "Complete Failure Test")

class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    def test_context_object_extraction_edge_cases(self):
        """Test edge cases in context object extraction"""
        # Test with object that has get method but no user_id key
        mock_dict_obj = {"name": "test", "email": "test@example.com"}
        result = _extract_user_id_from_context_object(mock_dict_obj)
        assert result is None
        
        # Test with object that has attributes but wrong types
        mock_obj = Mock()
        mock_obj.user_id = None
        result = _extract_user_id_from_context_object(mock_obj)
        assert result == "None"  # Converted to string
        
        # Test with complex object structure
        mock_nested_obj = Mock()
        mock_nested_obj.user_context = Mock()
        mock_nested_obj.user_context.user_id = "nested-user"
        # But no direct user_id or id
        if hasattr(mock_nested_obj, 'user_id'):
            delattr(mock_nested_obj, 'user_id')
        if hasattr(mock_nested_obj, 'id'):
            delattr(mock_nested_obj, 'id')
        
        result = _extract_user_id_from_context_object(mock_nested_obj)
        assert result is None  # Should not drill down into nested objects
    
    def test_request_state_edge_cases(self):
        """Test edge cases in request state handling"""
        with patch('fastmcp.task_management.interface.controllers.auth_helper._current_http_request') as mock_current_request:
            # Test with request that has state but user_id extraction fails
            mock_request = Mock()
            mock_request.state = Mock()
            mock_context_obj = Mock()
            # Context object with no extractable user_id
            mock_context_obj.name = "test"
            if hasattr(mock_context_obj, 'user_id'):
                delattr(mock_context_obj, 'user_id')
            if hasattr(mock_context_obj, 'id'):
                delattr(mock_context_obj, 'id')
            mock_request.state.user_id = mock_context_obj
            mock_current_request.get.return_value = mock_request
            
            result = get_user_id_from_request_state()
            assert result is None

if __name__ == "__main__":
    pytest.main([__file__])