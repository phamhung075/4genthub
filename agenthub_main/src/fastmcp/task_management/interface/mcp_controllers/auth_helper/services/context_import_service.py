"""Context Import Service for Authentication"""

import logging

logger = logging.getLogger(__name__)


class ContextImportService:
    """Handle context middleware imports and availability checks"""
    
    def __init__(self):
        self.request_context_available = False
        self.user_context_available = False
        self.starlette_available = False
        
        # Import functions as stubs
        self.get_user_from_request_context = lambda: None
        self.get_current_user_email = lambda: None
        self.get_current_auth_method = lambda: None
        self.is_request_authenticated = lambda: False
        self.get_authentication_context = lambda: {}
        self.get_current_user_id = lambda: None
        
        self._setup_imports()
    
    def _setup_imports(self):
        """Setup all context imports"""
        self._import_request_context_middleware()
        self._import_user_context_middleware()
        self._import_starlette()
    
    def _import_request_context_middleware(self):
        """Import RequestContextMiddleware functions"""
        try:
            from fastmcp.auth.middleware.request_context_middleware import (
                get_current_user_id as get_user_from_request_context,
                get_current_user_email,
                get_current_auth_method,
                is_request_authenticated,
                get_authentication_context
            )
            self.request_context_available = True
            self.get_user_from_request_context = get_user_from_request_context
            self.get_current_user_email = get_current_user_email
            self.get_current_auth_method = get_current_auth_method
            self.is_request_authenticated = is_request_authenticated
            self.get_authentication_context = get_authentication_context
            logger.info("✅ RequestContextMiddleware context functions imported successfully")
        except ImportError as e:
            logger.warning(f"RequestContextMiddleware context functions not available: {e}")
    
    def _import_user_context_middleware(self):
        """Import custom user context middleware"""
        try:
            from fastmcp.auth.middleware.user_context_middleware import get_current_user_id
            self.user_context_available = True
            self.get_current_user_id = get_current_user_id
            logger.info("✅ User context middleware functions imported successfully")
        except ImportError as e:
            logger.warning(f"User context middleware functions not available: {e}")
    
    def _import_starlette(self):
        """Import Starlette for dual auth"""
        try:
            from starlette.requests import Request
            from starlette.middleware.base import RequestCycle
            self.starlette_available = True
        except ImportError:
            logger.debug("Starlette not available - request state not accessible")