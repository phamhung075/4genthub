"""
RequestContextMiddleware for Authentication Context Propagation

This middleware creates context variables that store authentication information
from DualAuthMiddleware, making it accessible to auth_helper.py and other components
throughout the request lifecycle.
"""

import logging
from contextvars import ContextVar
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variables for thread-safe authentication context storage
_current_user_id: ContextVar[Optional[str]] = ContextVar('current_user_id', default=None)
_current_user_email: ContextVar[Optional[str]] = ContextVar('current_user_email', default=None)
_current_auth_method: ContextVar[Optional[str]] = ContextVar('current_auth_method', default=None)
_current_auth_info: ContextVar[Optional[Dict[str, Any]]] = ContextVar('current_auth_info', default=None)
_request_authenticated: ContextVar[bool] = ContextVar('request_authenticated', default=False)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures authentication context from DualAuthMiddleware
    and makes it available throughout the request lifecycle via context variables.
    
    This middleware should be placed AFTER DualAuthMiddleware in the middleware stack
    so that authentication information is already processed and available in request.state.
    """
    
    def __init__(self, app):
        super().__init__(app)
        logger.info("RequestContextMiddleware initialized for authentication context propagation")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and capture authentication context from DualAuthMiddleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response
        """
        # Clear context variables at the start of each request
        _current_user_id.set(None)
        _current_user_email.set(None)
        _current_auth_method.set(None)
        _current_auth_info.set(None)
        _request_authenticated.set(False)
        
        logger.debug(f"🔧 REQUEST_CONTEXT: Processing request {request.method} {request.url.path}")
        
        try:
            # Capture authentication context BEFORE processing the request
            # DualAuthMiddleware should have already run and set request.state.user_id etc.
            self._capture_auth_context_from_request_state(request)
            
            # CRITICAL FIX: For MCP endpoints, also set user in ASGI scope for handle_streamable_http
            # The MCP handler expects user info in the scope dictionary, not just request.state
            if hasattr(request, 'state') and hasattr(request.state, 'user_id'):
                user_id = request.state.user_id
                if user_id and request.url.path.startswith('/mcp'):
                    # Set user in ASGI scope for MCP streamable HTTP handler
                    if hasattr(request, 'scope') and isinstance(request.scope, dict):
                        request.scope['user'] = {
                            'user_id': user_id,
                            'email': getattr(request.state.auth_info, 'email', None) if hasattr(request.state, 'auth_info') else None,
                            'auth_method': getattr(request.state, 'auth_type', 'unknown')
                        }
                        logger.debug(f"✅ REQUEST_CONTEXT: Set user in ASGI scope for MCP endpoint - user_id={user_id}")
            
            # Process the request through the middleware chain with context available
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ REQUEST_CONTEXT: Error processing request: {e}")
            # Clear context on error to prevent leakage
            self._clear_auth_context()
            raise
        finally:
            # Context variables will automatically be cleaned up when the request ends
            # due to how contextvars work in async contexts
            pass
    
    def _capture_auth_context_from_request_state(self, request: Request) -> None:
        """
        Capture authentication context from request.state (set by DualAuthMiddleware)
        and store it in context variables for access by auth_helper.py.
        
        Args:
            request: HTTP request with authentication state
        """
        try:
            # Check if DualAuthMiddleware set authentication info in request.state
            if hasattr(request, 'state'):
                user_id = getattr(request.state, 'user_id', None)
                auth_type = getattr(request.state, 'auth_type', None)
                auth_info = getattr(request.state, 'auth_info', None)
                
                if user_id:
                    # Set context variables from request state
                    _current_user_id.set(user_id)
                    _request_authenticated.set(True)
                    
                    # Extract additional info from auth_info if available
                    if auth_info and isinstance(auth_info, dict):
                        email = auth_info.get('email')
                        if email:
                            _current_user_email.set(email)
                        
                        auth_method = auth_info.get('auth_method', auth_type)
                        _current_auth_method.set(auth_method)
                        _current_auth_info.set(auth_info)
                    
                    logger.debug(f"✅ REQUEST_CONTEXT: Captured auth context - user_id={user_id}, auth_method={auth_type}")
                else:
                    logger.debug("🔍 REQUEST_CONTEXT: No user_id found in request.state - request not authenticated")
            else:
                logger.warning("⚠️ REQUEST_CONTEXT: No request.state available - cannot capture auth context")
                
        except Exception as e:
            logger.error(f"❌ REQUEST_CONTEXT: Error capturing auth context from request state: {e}")
            # Clear context on error to prevent inconsistent state
            self._clear_auth_context()
    
    def _clear_auth_context(self) -> None:
        """Clear all authentication context variables."""
        try:
            _current_user_id.set(None)
            _current_user_email.set(None)
            _current_auth_method.set(None)
            _current_auth_info.set(None)
            _request_authenticated.set(False)
            logger.debug("🧹 REQUEST_CONTEXT: Authentication context cleared")
        except Exception as e:
            logger.error(f"❌ REQUEST_CONTEXT: Error clearing auth context: {e}")


# Helper functions to access context variables from other modules
def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID from context variables.
    
    Returns:
        User ID if authenticated, None otherwise
    """
    try:
        user_id = _current_user_id.get()
        logger.debug(f"🔍 CONTEXT_ACCESS: get_current_user_id() returning: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error getting current user ID: {e}")
        return None


def get_current_user_email() -> Optional[str]:
    """
    Get the current user email from context variables.
    
    Returns:
        User email if authenticated and available, None otherwise
    """
    try:
        email = _current_user_email.get()
        logger.debug(f"🔍 CONTEXT_ACCESS: get_current_user_email() returning: {email}")
        return email
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error getting current user email: {e}")
        return None


def get_current_auth_method() -> Optional[str]:
    """
    Get the current authentication method from context variables.
    
    Returns:
        Authentication method if authenticated, None otherwise
    """
    try:
        auth_method = _current_auth_method.get()
        logger.debug(f"🔍 CONTEXT_ACCESS: get_current_auth_method() returning: {auth_method}")
        return auth_method
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error getting current auth method: {e}")
        return None


def get_current_auth_info() -> Optional[Dict[str, Any]]:
    """
    Get the complete authentication info from context variables.
    
    Returns:
        Full authentication info dict if authenticated, None otherwise
    """
    try:
        auth_info = _current_auth_info.get()
        logger.debug(f"🔍 CONTEXT_ACCESS: get_current_auth_info() returning: {bool(auth_info)}")
        return auth_info
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error getting current auth info: {e}")
        return None


def is_request_authenticated() -> bool:
    """
    Check if the current request is authenticated.
    
    Returns:
        True if request is authenticated, False otherwise
    """
    try:
        authenticated = _request_authenticated.get()
        logger.debug(f"🔍 CONTEXT_ACCESS: is_request_authenticated() returning: {authenticated}")
        return authenticated
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error checking authentication status: {e}")
        return False


def get_authentication_context() -> Dict[str, Any]:
    """
    Get all authentication context as a single dictionary.
    
    Returns:
        Dictionary containing all available authentication context
    """
    try:
        return {
            'user_id': get_current_user_id(),
            'email': get_current_user_email(),
            'auth_method': get_current_auth_method(),
            'auth_info': get_current_auth_info(),
            'authenticated': is_request_authenticated()
        }
    except Exception as e:
        logger.error(f"❌ CONTEXT_ACCESS: Error getting authentication context: {e}")
        return {
            'user_id': None,
            'email': None,
            'auth_method': None,
            'auth_info': None,
            'authenticated': False
        }


# Backward compatibility functions for old user_context_middleware
def get_current_user_context():
    """
    Backward compatibility function for get_current_user_context.
    Returns a simple object with user_id and email for compatibility.
    """
    try:
        user_id = get_current_user_id()
        email = get_current_user_email()
        if user_id:
            # Return a simple object that matches the old MCPUserContext interface
            class BackwardCompatUserContext:
                def __init__(self, user_id, email):
                    self.user_id = user_id
                    self.email = email
                    self.roles = []  # Default empty roles
            return BackwardCompatUserContext(user_id, email)
        return None
    except Exception as e:
        logger.error(f"Error in get_current_user_context: {e}")
        return None


def get_current_user_id_alias():
    """Alias for get_current_user_id for compatibility"""
    return get_current_user_id()


# Backward compatibility context variable
# This simulates the old current_user_context ContextVar
current_user_context = _current_user_id


# Factory function for easy middleware creation
def create_request_context_middleware():
    """
    Factory function to create RequestContextMiddleware.
    
    Returns:
        Configured middleware class
    """
    return RequestContextMiddleware