"""
Debug Service - Centralized Debugging Control

This service provides environment-based debugging controls that can be easily
enabled/disabled via .env configuration for troubleshooting production issues.
"""

import os
import logging
import time
import json
from typing import Dict, Any, Optional, Union
from functools import wraps


class DebugService:
    """Centralized debug service with environment-based controls."""
    
    def __init__(self):
        # Environment-based debug flags
        self.debug_enabled = os.getenv("DEBUG_SERVICE_ENABLED", "false").lower() == "true"
        self.debug_http = os.getenv("DEBUG_HTTP_REQUESTS", "false").lower() == "true"
        self.debug_api_v2 = os.getenv("DEBUG_API_V2", "false").lower() == "true"
        self.debug_mcp = os.getenv("DEBUG_MCP_TOOLS", "false").lower() == "true"
        self.debug_auth = os.getenv("DEBUG_AUTHENTICATION", "false").lower() == "true"
        self.debug_database = os.getenv("DEBUG_DATABASE", "false").lower() == "true"
        self.debug_frontend = os.getenv("DEBUG_FRONTEND_ISSUES", "false").lower() == "true"
        
        # Debug output controls
        self.debug_verbose = os.getenv("DEBUG_VERBOSE", "false").lower() == "true"
        self.debug_stack_traces = os.getenv("DEBUG_STACK_TRACES", "false").lower() == "true"
        
        # Create debug loggers
        self.logger = logging.getLogger("4genthub.debug.service")
        self.http_logger = logging.getLogger("4genthub.debug.http")
        self.api_logger = logging.getLogger("4genthub.debug.api")
        self.auth_logger = logging.getLogger("4genthub.debug.auth")
        self.db_logger = logging.getLogger("4genthub.debug.database")
        
        # Configure log levels based on debug flags
        if self.debug_enabled:
            self.logger.setLevel(logging.DEBUG)
            if self.debug_http:
                self.http_logger.setLevel(logging.DEBUG)
            if self.debug_api_v2:
                self.api_logger.setLevel(logging.DEBUG)
            if self.debug_auth:
                self.auth_logger.setLevel(logging.DEBUG)
            if self.debug_database:
                self.db_logger.setLevel(logging.DEBUG)
    
    def is_enabled(self, category: str = "general") -> bool:
        """Check if debug is enabled for a specific category."""
        if not self.debug_enabled:
            return False
        
        category_flags = {
            "general": True,
            "http": self.debug_http,
            "api_v2": self.debug_api_v2,
            "mcp": self.debug_mcp,
            "auth": self.debug_auth,
            "database": self.debug_database,
            "frontend": self.debug_frontend
        }
        
        return category_flags.get(category, False)
    
    def log_request(self, method: str, url: str, headers: Dict[str, str], 
                   body: Optional[str] = None, client_ip: str = "unknown"):
        """Log HTTP request details if debugging is enabled."""
        if not self.is_enabled("http"):
            return
        
        self.http_logger.debug("=" * 80)
        self.http_logger.debug(f"🌐 HTTP REQUEST: {method} {url}")
        self.http_logger.debug(f"📍 Client IP: {client_ip}")
        
        # Log important headers
        important_headers = ["authorization", "content-type", "user-agent", "origin", "referer"]
        for header in important_headers:
            if header in headers:
                value = headers[header]
                # Mask authorization tokens for security
                if header == "authorization" and value.startswith("Bearer "):
                    value = f"Bearer {value[7:15]}...{value[-8:]}" if len(value) > 23 else "Bearer [MASKED]"
                self.http_logger.debug(f"🔧 {header.title()}: {value}")
        
        if body and self.debug_verbose:
            try:
                if headers.get("content-type", "").startswith("application/json"):
                    body_json = json.loads(body)
                    self.http_logger.debug("📦 Request Body:")
                    self.http_logger.debug(json.dumps(body_json, indent=2))
                else:
                    self.http_logger.debug(f"📦 Request Body: {body[:500]}...")
            except Exception as e:
                self.http_logger.debug(f"📦 Request Body (raw): {body[:200]}... [Parse error: {e}]")
    
    def log_response(self, status_code: int, headers: Dict[str, str], 
                    body: Optional[str] = None, duration: float = 0.0):
        """Log HTTP response details if debugging is enabled."""
        if not self.is_enabled("http"):
            return
        
        status_icon = "✅" if status_code < 400 else "❌"
        self.http_logger.debug(f"{status_icon} RESPONSE: {status_code} ({duration:.3f}s)")
        
        if body and self.debug_verbose:
            try:
                if headers.get("content-type", "").startswith("application/json"):
                    body_json = json.loads(body)
                    self.http_logger.debug("📦 Response Body:")
                    self.http_logger.debug(json.dumps(body_json, indent=2))
                else:
                    self.http_logger.debug(f"📦 Response Body: {body[:500]}...")
            except Exception as e:
                self.http_logger.debug(f"📦 Response Body (raw): {body[:200]}... [Parse error: {e}]")
        
        self.http_logger.debug("=" * 80)
    
    def log_api_v2_request(self, endpoint: str, user_id: Optional[str], 
                          method: str, params: Dict[str, Any]):
        """Log API V2 request details if debugging is enabled."""
        if not self.is_enabled("api_v2"):
            return
        
        self.api_logger.debug("=" * 80)
        self.api_logger.debug(f"🔗 API V2 REQUEST: {method} {endpoint}")
        self.api_logger.debug(f"👤 User ID: {user_id or 'Anonymous'}")
        self.api_logger.debug(f"📋 Parameters: {json.dumps(params, indent=2) if params else 'None'}")
    
    def log_api_v2_response(self, endpoint: str, success: bool, 
                           data: Optional[Dict[str, Any]], error: Optional[str] = None):
        """Log API V2 response details if debugging is enabled."""
        if not self.is_enabled("api_v2"):
            return
        
        status_icon = "✅" if success else "❌"
        self.api_logger.debug(f"{status_icon} API V2 RESPONSE: {endpoint}")
        
        if success and data:
            if "tasks" in data:
                task_count = len(data.get("tasks", []))
                self.api_logger.debug(f"📋 Tasks returned: {task_count}")
                if task_count > 0 and self.debug_verbose:
                    first_task = data["tasks"][0]
                    self.api_logger.debug(f"📝 First task: {first_task.get('title', 'N/A')} [{first_task.get('status', 'N/A')}]")
            elif "projects" in data:
                project_count = len(data.get("projects", []))
                self.api_logger.debug(f"📁 Projects returned: {project_count}")
        elif error:
            self.api_logger.debug(f"🚨 Error: {error}")
        
        self.api_logger.debug("=" * 80)
    
    def log_auth_event(self, event: str, user_id: Optional[str] = None, 
                      token_info: Optional[Dict[str, Any]] = None, 
                      error: Optional[str] = None):
        """Log authentication events if debugging is enabled."""
        if not self.is_enabled("auth"):
            return
        
        self.auth_logger.debug("=" * 80)
        self.auth_logger.debug(f"🔐 AUTH EVENT: {event}")
        self.auth_logger.debug(f"👤 User ID: {user_id or 'Unknown'}")
        
        if token_info:
            # Log safe token information (no actual tokens)
            safe_info = {
                "valid": token_info.get("valid"),
                "expires_at": token_info.get("expires_at"),
                "usage_count": token_info.get("usage_count")
            }
            self.auth_logger.debug(f"🎫 Token Info: {json.dumps(safe_info, indent=2)}")
        
        if error:
            self.auth_logger.debug(f"🚨 Auth Error: {error}")
            if self.debug_stack_traces:
                import traceback
                self.auth_logger.debug("🔍 Stack Trace:")
                for line in traceback.format_exc().splitlines():
                    self.auth_logger.debug(f"   {line}")
        
        self.auth_logger.debug("=" * 80)
    
    def log_database_event(self, operation: str, table: Optional[str] = None, 
                          query_info: Optional[Dict[str, Any]] = None,
                          result_count: Optional[int] = None,
                          error: Optional[str] = None):
        """Log database operations if debugging is enabled."""
        if not self.is_enabled("database"):
            return
        
        self.db_logger.debug("=" * 80)
        self.db_logger.debug(f"💾 DATABASE: {operation}")
        
        if table:
            self.db_logger.debug(f"📊 Table: {table}")
        
        if query_info:
            self.db_logger.debug(f"🔍 Query Info: {json.dumps(query_info, indent=2)}")
        
        if result_count is not None:
            self.db_logger.debug(f"📊 Results: {result_count} rows")
        
        if error:
            self.db_logger.debug(f"🚨 DB Error: {error}")
            if self.debug_stack_traces:
                import traceback
                self.db_logger.debug("🔍 Stack Trace:")
                for line in traceback.format_exc().splitlines():
                    self.db_logger.debug(f"   {line}")
        
        self.db_logger.debug("=" * 80)
    
    def log_frontend_issue(self, issue_type: str, details: Dict[str, Any], 
                          user_context: Optional[Dict[str, Any]] = None):
        """Log frontend-specific issues if debugging is enabled."""
        if not self.is_enabled("frontend"):
            return
        
        self.logger.debug("=" * 80)
        self.logger.debug(f"🖥️ FRONTEND ISSUE: {issue_type}")
        
        if user_context:
            self.logger.debug(f"👤 User Context: {json.dumps(user_context, indent=2)}")
        
        self.logger.debug(f"📝 Issue Details: {json.dumps(details, indent=2)}")
        self.logger.debug("=" * 80)
    
    def debug_decorator(self, category: str = "general"):
        """Decorator to add debug logging to functions."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.is_enabled(category):
                    return func(*args, **kwargs)
                
                start_time = time.time()
                self.logger.debug(f"🔧 CALLING: {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self.logger.debug(f"✅ COMPLETED: {func.__name__} ({duration:.3f}s)")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self.logger.debug(f"❌ FAILED: {func.__name__} ({duration:.3f}s) - {str(e)}")
                    if self.debug_stack_traces:
                        import traceback
                        for line in traceback.format_exc().splitlines():
                            self.logger.debug(f"   {line}")
                    raise
            
            return wrapper
        return decorator
    
    def get_debug_status(self) -> Dict[str, Any]:
        """Get current debug configuration status."""
        return {
            "debug_enabled": self.debug_enabled,
            "categories": {
                "http": self.debug_http,
                "api_v2": self.debug_api_v2,
                "mcp": self.debug_mcp,
                "auth": self.debug_auth,
                "database": self.debug_database,
                "frontend": self.debug_frontend
            },
            "options": {
                "verbose": self.debug_verbose,
                "stack_traces": self.debug_stack_traces
            }
        }


# Global debug service instance
debug_service = DebugService()

# Convenience functions for easy import
def log_request(*args, **kwargs):
    return debug_service.log_request(*args, **kwargs)

def log_response(*args, **kwargs):
    return debug_service.log_response(*args, **kwargs)

def log_api_v2_request(*args, **kwargs):
    return debug_service.log_api_v2_request(*args, **kwargs)

def log_api_v2_response(*args, **kwargs):
    return debug_service.log_api_v2_response(*args, **kwargs)

def log_auth_event(*args, **kwargs):
    return debug_service.log_auth_event(*args, **kwargs)

def log_database_event(*args, **kwargs):
    return debug_service.log_database_event(*args, **kwargs)

def log_frontend_issue(*args, **kwargs):
    return debug_service.log_frontend_issue(*args, **kwargs)

def debug_decorator(category: str = "general"):
    return debug_service.debug_decorator(category)

def is_debug_enabled(category: str = "general") -> bool:
    return debug_service.is_enabled(category)

def get_debug_status() -> Dict[str, Any]:
    return debug_service.get_debug_status()