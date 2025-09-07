#!/usr/bin/env python3
"""
MCP Entry Point for FastMCP Server with Consolidated Tools

This script serves as the entry point for running the FastMCP server with
integrated task management, agent orchestration, and authentication.
"""

import logging
import sys
import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Load environment variables from .env file FIRST
try:
    from dotenv import load_dotenv
    # Load from the parent directory where .env is located
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        # Try loading from current directory
        load_dotenv()
        print("✅ Loaded environment variables from current directory")
except ImportError:
    print("⚠️ python-dotenv not available - using environment variables only")
except Exception as e:
    print(f"⚠️ Failed to load .env file: {e}")

# Import the FastMCP server class directly
from fastmcp.server.server import FastMCP
from fastmcp.utilities.logging import configure_logging

# Import authentication system
from fastmcp.auth import AuthMiddleware, TokenValidator, TokenValidationError, RateLimitError

# Import connection management tools
from .connection_manager import get_connection_manager, cleanup_connection_manager

# Import Starlette components for middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp


class DebugLoggingMiddleware:
    """Enhanced debug logging middleware for HTTP requests and responses."""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("dhafnck.debug.http")
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Capture request details
        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()
        client = scope.get("client", ["unknown", 0])
        
        # Build full URL
        url = f"http://{scope.get('server', ['localhost', 8000])[0]}:{scope.get('server', ['localhost', 8000])[1]}{path}"
        if query_string:
            url += f"?{query_string}"
        
        # Log request headers
        headers = dict(scope.get("headers", []))
        
        self.logger.debug("=" * 80)
        self.logger.debug(f"🔍 INCOMING REQUEST: {method} {url}")
        self.logger.debug(f"📍 Client: {client[0]}:{client[1]}")
        
        # Log important headers
        for header_name, header_value in headers.items():
            header_str = header_name.decode() if isinstance(header_name, bytes) else header_name
            value_str = header_value.decode() if isinstance(header_value, bytes) else header_value
            
            if header_str.lower() in ['user-agent', 'content-type', 'content-length', 'authorization', 'mcp-session-id']:
                self.logger.debug(f"🔧 {header_str.title()}: {value_str}")
        
        # Log all headers for debugging
        self.logger.debug("📝 Request Headers:")
        for header_name, header_value in headers.items():
            header_str = header_name.decode() if isinstance(header_name, bytes) else header_name
            value_str = header_value.decode() if isinstance(header_value, bytes) else header_value
            self.logger.debug(f"   {header_str}: {value_str}")
        
        # Capture request body
        body = b""
        
        async def receive_wrapper():
            nonlocal body
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"")
                body += chunk
            return message
        
        # Capture response
        response_started = False
        response_completed = False
        status_code = None
        response_headers = {}
        response_body = b""
        
        async def send_wrapper(message):
            nonlocal response_started, response_completed, status_code, response_headers, response_body
            
            # Don't send anything if response is already completed
            if response_completed:
                self.logger.warning(f"⚠️ Attempted to send {message['type']} after response completed")
                return
            
            if message["type"] == "http.response.start":
                if response_started:
                    self.logger.error("❌ Duplicate http.response.start detected")
                    return
                response_started = True
                status_code = message["status"]
                response_headers = dict(message.get("headers", []))
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                response_body += chunk
                
                # If this is the last chunk, mark response as completed
                if not message.get("more_body", False):
                    response_completed = True
                    await self._log_response(status_code, response_headers, response_body, url)
            
            await send(message)
        
        # Log request body if present
        start_time = time.time()
        
        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as e:
            self.logger.error(f"❌ EXCEPTION in request processing: {e}")
            raise
        finally:
            # Log request body after processing
            if body:
                try:
                    if headers.get(b'content-type', b'').startswith(b'application/json'):
                        import json
                        body_json = json.loads(body.decode())
                        self.logger.debug("📦 Request Body (JSON):")
                        self.logger.debug(json.dumps(body_json, indent=2))
                    else:
                        self.logger.debug(f"📦 Request Body: {body.decode()[:500]}...")
                except Exception as e:
                    self.logger.debug(f"📦 Request Body (raw): {body[:200]}...")
    
    async def _log_response(self, status_code, response_headers, response_body, url):
        """Log response details."""
        duration = time.time() - getattr(self, '_start_time', time.time())
        
        # Decode headers
        headers_dict = {}
        for header_name, header_value in response_headers.items():
            header_str = header_name.decode() if isinstance(header_name, bytes) else header_name
            value_str = header_value.decode() if isinstance(header_value, bytes) else header_value
            headers_dict[header_str] = value_str
        
        # Log response status and timing
        if status_code >= 400:
            self.logger.debug(f"❌ RESPONSE: {status_code} ({duration:.3f}s)")
        else:
            self.logger.debug(f"✅ RESPONSE: {status_code} ({duration:.3f}s)")
        
        # Log response headers
        content_type = headers_dict.get('content-type', 'Not provided')
        self.logger.debug(f"📋 Response Content-Type: {content_type}")
        
        self.logger.debug("📝 Response Headers:")
        for header_name, header_value in headers_dict.items():
            self.logger.debug(f"   {header_name}: {header_value}")
        
        # Log response body for errors or if it's JSON
        if response_body:
            try:
                if content_type.startswith('application/json') or status_code >= 400:
                    import json
                    body_json = json.loads(response_body.decode())
                    self.logger.debug("📦 Response Body (JSON):")
                    self.logger.debug(json.dumps(body_json, indent=2))
                else:
                    self.logger.debug(f"📦 Response Body: {response_body.decode()[:500]}...")
            except Exception as e:
                self.logger.debug(f"📦 Response Body (raw): {response_body[:200]}...")
        
        if status_code >= 400:
            self.logger.error(f"❌ ERROR RESPONSE: {status_code}")
            if not response_body:
                self.logger.error("❌ No response body provided for error")
            self.logger.error("❌ Check application logs for error details")
        
        self.logger.debug("=" * 80)


def create_dhafnck_mcp_server() -> FastMCP:
    """Create and configure the DhafnckMCP server with all consolidated tools."""
    
    # Configure logging with enhanced debug capabilities
    log_level = os.environ.get("FASTMCP_LOG_LEVEL", "INFO")
    configure_logging(level=log_level)
    
    # Configure root logger to catch all logs
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Add handler to root logger if it doesn't have one
    if not root_logger.handlers:
        root_handler = logging.StreamHandler(sys.stderr)
        root_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        root_handler.setFormatter(root_formatter)
        root_logger.addHandler(root_handler)
    
    # Create additional debug logger for HTTP requests
    debug_logger = logging.getLogger("dhafnck.debug.http")
    debug_handler = logging.StreamHandler()
    debug_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    debug_handler.setFormatter(debug_formatter)
    debug_logger.addHandler(debug_handler)
    debug_logger.setLevel(logging.DEBUG)
    
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing DhafnckMCP server with consolidated tools and authentication...")
    logger.info(f"Log level: {log_level}")
    
    # Initialize database before server startup
    try:
        from fastmcp.task_management.infrastructure.database.init_database import init_database
        logger.info("Initializing database...")
        init_database()
        logger.info("Database initialized successfully")
        
        # Run schema validation after database initialization
        logger.info("Running database schema validation...")
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from fastmcp.task_management.infrastructure.database.schema_validator import validate_schema_on_startup
        import asyncio
        
        db_config = get_db_config()
        if db_config and db_config.engine:
            validation_result = asyncio.run(validate_schema_on_startup(db_config.engine))
            if not validation_result:
                logger.warning("Schema validation failed - some database operations may fail")
            else:
                logger.info("Schema validation completed successfully")
        else:
            logger.warning("Could not get database engine for schema validation")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Don't exit - let the server start and handle the error gracefully
        logger.warning("Server will continue with potential database issues")
    
    # Check if authentication is enabled
    auth_enabled = os.environ.get("DHAFNCK_AUTH_ENABLED", "true").lower() == "true"
    
    # Check Supabase configuration
    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url and auth_enabled:
        logger.warning("No Supabase configuration found but auth requested - forcing auth_enabled=False")
        auth_enabled = False
    
    # Log final auth decision
    logger.info(f"Authentication enabled: {auth_enabled} (DHAFNCK_AUTH_ENABLED={os.environ.get('DHAFNCK_AUTH_ENABLED', 'true')}, Supabase={'configured' if supabase_url else 'not configured'})")
    
    # Initialize authentication middleware with JWT secret key
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
    auth_middleware = AuthMiddleware(secret_key=jwt_secret_key)
    
    # Create FastMCP server with task management disabled (we'll register DDD tools manually)
    server = FastMCP(
        name="DhafnckMCP - Task Management & Agent Orchestration",
        instructions=(
            "A comprehensive MCP server providing task management, project management, "
            "agent orchestration, cursor rules integration, and secure authentication. "
            "This server includes tools for managing projects, tasks, subtasks, agents, "
            "automated rule generation, and token-based authentication."
        ),
        version="2.1.0",
        # DISABLE automatic task management - we'll register DDD tools manually
        enable_task_management=False,
        # Use environment variables for configuration
        task_repository=None,  # Will use default JsonTaskRepository
        projects_file_path=os.environ.get("PROJECTS_FILE_PATH"),
        # Suppress duplicate tool warnings since task management tools are registered automatically
        on_duplicate_tools="ignore",
        
        # --- AUTHENTICATION CONFIGURATION ---
        # Pass authentication middleware to the server
        auth=auth_middleware if auth_enabled else None,
        
        # --- DEPRECATED SETTINGS (but required for compatibility) ---
        # Enable JSON response for compatibility with JSON-only MCP clients like Cursor
        json_response=True,
        # Enable debug mode for better error reporting and logging
        debug=True,
        # Set log level for detailed debugging
        log_level="DEBUG",
        # Enable stateless HTTP mode to bypass session validation issues
        stateless_http=True,
    )
    
    # Register DDD-compliant task management tools manually
    logger.info("Registering DDD-compliant task management tools...")
    try:
        from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
        ddd_tools = DDDCompliantMCPTools()
        ddd_tools.register_tools(server)
        logger.info("DDD-compliant task management tools registered successfully")
    except Exception as e:
        logger.error(f"Failed to register DDD task management tools: {e}")
        logger.error("Server will continue without task management tools")
    
    # Add authentication tools (conditionally registered)
    logger.info(f"Authentication enabled: {auth_enabled}")
    
    if auth_enabled:
        @server.tool()
        async def validate_token(token: str) -> dict:
            """
            Validate an authentication token.
            
            Args:
                token: The authentication token to validate
                
            Returns:
                Token validation result with user information
            """
            try:
                token_info = await auth_middleware.authenticate_request(token)
                
                if not token_info:
                    return {
                        "valid": True,
                        "message": "Authentication disabled or MVP mode",
                        "user_id": "mvp_user",
                        "auth_enabled": auth_middleware.enabled
                    }
                
                return {
                    "valid": True,
                    "user_id": token_info.user_id,
                    "created_at": token_info.created_at.isoformat(),
                    "expires_at": token_info.expires_at.isoformat() if token_info.expires_at else None,
                    "usage_count": token_info.usage_count,
                    "last_used": token_info.last_used.isoformat() if token_info.last_used else None,
                    "auth_enabled": auth_middleware.enabled
                }
                
            except TokenValidationError as e:
                return {
                    "valid": False,
                    "error": str(e),
                    "error_type": "validation_error",
                    "auth_enabled": auth_middleware.enabled
                }
            except RateLimitError as e:
                return {
                    "valid": False,
                    "error": str(e),
                    "error_type": "rate_limit_error",
                    "auth_enabled": auth_middleware.enabled
                }
            except Exception as e:
                logger.error(f"Token validation error: {e}")
                return {
                    "valid": False,
                    "error": "Internal validation error",
                    "error_type": "internal_error",
                    "auth_enabled": auth_middleware.enabled
                }
        
        @server.tool()
        async def get_rate_limit_status(token: str) -> dict:
            """
            Get rate limit status for a token.
            
            Args:
                token: The authentication token
                
            Returns:
                Current rate limit status
            """
            try:
                status = await auth_middleware.get_rate_limit_status(token)
                return {
                    "success": True,
                    "rate_limits": status
                }
            except Exception as e:
                logger.error(f"Rate limit status error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @server.tool()
        async def revoke_token(token: str) -> dict:
            """
            Revoke an authentication token.
            
            Args:
                token: The token to revoke
                
            Returns:
                Revocation result
            """
            try:
                success = await auth_middleware.revoke_token(token)
                return {
                    "success": success,
                    "message": "Token revoked successfully" if success else "Failed to revoke token"
                }
            except Exception as e:
                logger.error(f"Token revocation error: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @server.tool()
        def get_auth_status() -> dict:
            """
            Get authentication system status.
            
            Returns:
                Authentication system status and configuration
            """
            return auth_middleware.get_auth_status()
        
        @server.tool()
        def generate_token() -> dict:
            """
            Generate a new secure authentication token.
            
            NOTE: Token generation is now handled through the API at /api/v2/tokens
            This MCP tool is deprecated and will return an informative message.
            
            Returns:
                Information about how to generate tokens
            """
            return {
                "success": False,
                "error": "Token generation via MCP tool is deprecated",
                "message": (
                    "Please use the API endpoint POST /api/v2/tokens to generate tokens. "
                    "This provides better security and integration with the authentication system."
                ),
                "api_endpoint": "/api/v2/tokens",
                "method": "POST",
                "example": {
                    "name": "my-token",
                    "expires_in_days": 30,
                    "scopes": ["read", "write"]
                }
            }
    else:
        logger.info("Authentication disabled - skipping auth tools registration")
    
    
    # Add HTTP health endpoint for container health checks
    @server.custom_route("/health", methods=["GET"])
    async def health_endpoint(request) -> JSONResponse:
        """HTTP health check endpoint for container health checks.
        
        Returns:
            Simple health status for load balancers and container orchestration
        """
        
        # Get basic health status
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "server": server.name,
            "version": "2.1.0"
        }
        
        # Add authentication status based on environment configuration
        auth_status = os.environ.get("DHAFNCK_AUTH_ENABLED", "true")
        supabase_configured = bool(os.environ.get("SUPABASE_URL"))
        health_data["auth_enabled"] = auth_status.lower() == "true" and supabase_configured
        
        # Add connection manager status if available
        try:
            connection_manager = await get_connection_manager()
            connection_stats = await connection_manager.get_connection_stats()
            reconnection_info = await connection_manager.get_reconnection_info()
            
            health_data["connections"] = {
                "active_connections": connection_stats["connections"]["active_connections"],
                "server_restart_count": connection_stats["server_info"]["restart_count"],
                "uptime_seconds": connection_stats["server_info"]["uptime_seconds"],
                "recommended_action": reconnection_info["recommended_action"]
            }
            
            # Add status broadcaster information
            from .connection_status_broadcaster import get_status_broadcaster
            status_broadcaster = await get_status_broadcaster()
            last_status = status_broadcaster.get_last_status()
            
            health_data["status_broadcasting"] = {
                "active": True,
                "registered_clients": status_broadcaster.get_client_count(),
                "last_broadcast": last_status.get("event_type") if last_status else None,
                "last_broadcast_time": last_status.get("timestamp") if last_status else None
            }
            
        except Exception as e:
            health_data["connections"] = {"error": str(e)}
            health_data["status_broadcasting"] = {"active": False, "error": str(e)}
        
        return JSONResponse(health_data)
    
    
    # Register DDD-compliant connection management tools
    try:
        from ..connection_management.interface.ddd_compliant_connection_tools import register_ddd_connection_tools
        register_ddd_connection_tools(server)
        logger.info("DDD-compliant connection management tools registered")
    except ImportError as e:
        logger.warning(f"Could not import DDD connection tools, falling back to legacy: {e}")
        # Fallback to legacy connection management tools
        from .manage_connection_tool import register_manage_connection_tool
        register_manage_connection_tool(server)
        logger.info("Legacy connection management tools registered")
    
    # Initialize connection manager and status broadcaster
    async def initialize_connection_manager():
        """Initialize the connection manager and status broadcaster on server startup"""
        try:
            # Initialize connection manager
            connection_manager = await get_connection_manager()
            await connection_manager.handle_server_restart()
            logger.info("Connection manager initialized and restart handled")
            
            # Initialize status broadcaster
            from .connection_status_broadcaster import get_status_broadcaster
            status_broadcaster = await get_status_broadcaster(connection_manager)
            await status_broadcaster.broadcast_server_restart()
            logger.info("Status broadcaster initialized and server restart broadcasted")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection manager and status broadcaster: {e}")
    
    # Add startup hook to initialize connection manager and status broadcaster
    if hasattr(server, '_startup_hooks'):
        server._startup_hooks.append(initialize_connection_manager)
    else:
        server._startup_hooks = [initialize_connection_manager]
    
    logger.info("DhafnckMCP server initialized successfully with authentication and connection management")
    return server


def main():
    """Main entry point for the MCP server."""
    
    # Initialize logger first
    logger = logging.getLogger(__name__)
    
    try:
        # Set debug logging for troubleshooting
        os.environ.setdefault("FASTMCP_LOG_LEVEL", "DEBUG")
        
        # Create the server
        server = create_dhafnck_mcp_server()
        
        # Log startup information
        logger.info("Starting DhafnckMCP server with authentication...")
        
        # Tools are registered manually now, not through server.consolidated_tools
        logger.info("DDD-compliant task management tools have been registered")
        
        # Log authentication status
        auth_status = os.environ.get("DHAFNCK_AUTH_ENABLED", "true")
        mvp_mode = os.environ.get("DHAFNCK_MVP_MODE", "false")
        supabase_configured = bool(os.environ.get("SUPABASE_URL"))
        
        # Convert auth status to boolean
        auth_enabled = auth_status.lower() in ("true", "1", "yes", "on")
        
        logger.info(f"Authentication: {auth_status}, MVP Mode: {mvp_mode}, Supabase: {supabase_configured}")
        
        # Determine transport from environment or command line arguments
        transport = os.environ.get("FASTMCP_TRANSPORT", "stdio")
        host = os.environ.get("FASTMCP_HOST", "localhost")
        port = int(os.environ.get("FASTMCP_PORT", "8000"))
        
        # Parse command line arguments for transport override
        if len(sys.argv) > 1:
            for i, arg in enumerate(sys.argv[1:], 1):
                if arg == "--transport" and i + 1 < len(sys.argv):
                    transport = sys.argv[i + 1]
                elif arg.startswith("--transport="):
                    transport = arg.split("=", 1)[1]
        
        logger.info(f"Starting server with transport: {transport}")
        
        if transport == "streamable-http":
            logger.info(f"HTTP server will bind to {host}:{port}")
            logger.info("Debug logging enabled for HTTP requests")
            
            # Configure middleware for HTTP mode
            from starlette.middleware import Middleware
            
            # Build middleware stack
            # IMPORTANT: Middleware executes in REVERSE order of addition!
            # Last added = First executed
            middleware_stack = []
            
            # Step 1: Add DualAuth middleware FIRST (runs first to process JWT tokens)
            if auth_enabled:
                try:
                    from fastmcp.auth.middleware.dual_auth_middleware import DualAuthMiddleware
                    
                    # Add DualAuthMiddleware first so JWT tokens are processed and request.state.user_id is set
                    middleware_stack.append(Middleware(DualAuthMiddleware))
                    logger.info("DualAuthMiddleware added for JWT token processing and user context extraction")
                except Exception as e:
                    logger.error(f"Failed to add DualAuthMiddleware: {e}")
                    logger.warning("Authentication may not work properly without DualAuthMiddleware")
            
            # Step 2: Add RequestContextMiddleware SECOND (runs after DualAuth to capture auth context)
            # This runs AFTER DualAuthMiddleware processes authentication and sets request.state
            try:
                from fastmcp.auth.middleware.request_context_middleware import RequestContextMiddleware
                middleware_stack.append(Middleware(RequestContextMiddleware))
                logger.info("RequestContextMiddleware added for authentication context propagation")
            except ImportError as e:
                logger.warning(f"Could not add RequestContextMiddleware: {e}")
                # Fallback to legacy RequestContextMiddleware if new one not available
                try:
                    from fastmcp.server.http_server import RequestContextMiddleware as LegacyRequestContextMiddleware
                    middleware_stack.append(Middleware(LegacyRequestContextMiddleware))
                    logger.info("Legacy RequestContextMiddleware added as fallback")
                except ImportError as fallback_e:
                    logger.warning(f"Could not add fallback RequestContextMiddleware: {fallback_e}")
            
            # Add debug middleware
            middleware_stack.append(Middleware(DebugLoggingMiddleware))
            
            # Get log level from environment
            server_log_level = os.environ.get("FASTMCP_LOG_LEVEL", "INFO").upper()
            
            # For streamable-http transport, pass the middleware stack
            # Authentication is handled by the FastMCP server's built-in auth parameter
            server.run(
                transport="streamable-http", 
                host=host, 
                port=port,
                # Use configurable log level from environment variable
                log_level=server_log_level,
                # Pass middleware stack for HTTP request processing
                middleware=middleware_stack
            )
        else:
            # For stdio transport (standard MCP)
            logger.info("Starting server in stdio mode for MCP communication")
            server.run(
                transport="stdio"
            )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 