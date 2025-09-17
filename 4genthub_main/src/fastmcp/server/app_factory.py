"""
FastAPI Application Factory
Creates and configures FastAPI applications with consistent settings.
"""

import os
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastmcp.config.version import VERSION
from fastmcp.config.cors_factory import cors_factory

logger = logging.getLogger(__name__)


class AppFactory:
    """Factory for creating configured FastAPI applications."""

    @staticmethod
    def create_app(
        title: str = "4genthub Server",
        description: str = "Unified MCP and API server",
        version: str = VERSION,
        enable_cors: bool = True,
        enable_auth: bool = True,
    ) -> FastAPI:
        """
        Create a configured FastAPI application.

        Args:
            title: Application title
            description: Application description
            version: Application version
            enable_cors: Whether to enable CORS middleware
            enable_auth: Whether to enable authentication

        Returns:
            Configured FastAPI application
        """
        # Create FastAPI app
        app = FastAPI(
            title=title,
            description=description,
            version=version,
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )

        # Configure CORS using factory
        if enable_cors:
            cors_factory.configure_cors(app)
            logger.info("✅ CORS configured using factory pattern")

        # Initialize services
        AppFactory._initialize_services(app, enable_auth)

        # Register routes
        AppFactory._register_routes(app)

        # Add health check
        AppFactory._add_health_check(app)

        logger.info(f"✅ {title} application created successfully")
        return app

    @staticmethod
    def _initialize_services(app: FastAPI, enable_auth: bool) -> None:
        """Initialize backend services."""
        # Store services in app state for access in endpoints
        app.state.mcp_auth = None
        app.state.mcp_tools = None
        app.state.security = HTTPBearer() if enable_auth else None

        try:
            # Initialize database
            from fastmcp.task_management.infrastructure.database.db_initializer import initialize_database_on_startup
            logger.info("Initializing database...")
            if initialize_database_on_startup():
                logger.info("✅ Database initialized successfully")
            else:
                logger.warning("⚠️ Database initialization failed - continuing with limited functionality")

            # Initialize authentication if enabled
            if enable_auth:
                auth_provider = os.getenv("AUTH_PROVIDER", "keycloak").lower()

                if auth_provider == "keycloak":
                    from fastmcp.auth.mcp_keycloak_auth import mcp_auth as keycloak_auth
                    app.state.mcp_auth = keycloak_auth
                    logger.info("✅ Keycloak authentication initialized")
                elif auth_provider == "supabase":
                    try:
                        from fastmcp.auth.supabase_auth import mcp_auth as supabase_auth
                        app.state.mcp_auth = supabase_auth
                        logger.info("✅ Supabase authentication initialized")
                    except ImportError:
                        logger.warning("Supabase auth not available, falling back to Keycloak")
                        from fastmcp.auth.mcp_keycloak_auth import mcp_auth as keycloak_auth
                        app.state.mcp_auth = keycloak_auth
                else:
                    logger.warning(f"Unknown auth provider: {auth_provider}")

            # Initialize MCP tools
            from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
            app.state.mcp_tools = DDDCompliantMCPTools()
            logger.info("✅ MCP tools initialized")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            # Continue with limited functionality

    @staticmethod
    def _register_routes(app: FastAPI) -> None:
        """Register all application routes."""
        try:
            # Register authentication routes
            from fastmcp.auth.interface.auth_endpoints import router as auth_router
            app.include_router(auth_router)
            logger.info("✅ Auth routes registered at /api/auth")

            # Register token management routes at /api/v2/tokens
            from fastmcp.server.routes.token_router import router as token_router
            app.include_router(token_router)
            logger.info("✅ Token management routes registered at /api/v2/tokens")
            # Token management routes are now handled by /api/v2/tokens router

            # Register API v2 routes
            try:
                from fastmcp.server.routes.agent_routes import router as agent_router
                app.include_router(agent_router)
                logger.info("✅ Agent routes registered at /api/v2/agents")
            except ImportError as e:
                logger.debug(f"Agent routes not available: {e}")

            try:
                from fastmcp.server.routes.project_routes import router as project_router
                app.include_router(project_router)
                logger.info("✅ Project routes registered")
            except ImportError as e:
                logger.debug(f"Project routes not available: {e}")

            try:
                from fastmcp.server.routes.task_user_routes import router as task_router
                app.include_router(task_router)
                logger.info("✅ Task routes registered")
            except ImportError as e:
                logger.debug(f"Task routes not available: {e}")

            # Register MCP endpoints
            AppFactory._register_mcp_endpoints(app)

        except Exception as e:
            logger.error(f"Failed to register routes: {e}")

    @staticmethod
    def _register_mcp_endpoints(app: FastAPI) -> None:
        """Register MCP tool endpoints."""
        from typing import Dict, Any

        async def get_authenticated_user(
            credentials: HTTPAuthorizationCredentials = None
        ) -> Dict[str, Any]:
            """Get authenticated user."""
            if not app.state.security or not credentials:
                return {"sub": "anonymous", "id": "anonymous"}

            token = credentials.credentials

            # Try hook authentication first
            try:
                from fastmcp.auth.hook_auth import hook_auth_validator
                user_data = hook_auth_validator.validate_hook_token(token)
                return user_data
            except:
                pass

            # Try provider authentication
            if app.state.mcp_auth:
                try:
                    user_data = await app.state.mcp_auth.validate_mcp_token(token)
                    return user_data
                except:
                    pass

            raise HTTPException(status_code=401, detail="Authentication failed")

        # Register MCP endpoints
        @app.post("/mcp/manage_task")
        async def manage_task(request: Dict[str, Any],
                            credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = await app.state.mcp_tools.manage_task(**request)
            return result

        @app.post("/mcp/manage_context")
        async def manage_context(request: Dict[str, Any],
                               credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.manage_context(**request)
            return result

        @app.post("/mcp/manage_project")
        async def manage_project(request: Dict[str, Any],
                               credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.manage_project(**request)
            return result

        @app.post("/mcp/manage_git_branch")
        async def manage_git_branch(request: Dict[str, Any],
                                  credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.manage_git_branch(**request)
            return result

        @app.post("/mcp/manage_subtask")
        async def manage_subtask(request: Dict[str, Any],
                               credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.manage_subtask(**request)
            return result

        @app.post("/mcp/call_agent")
        async def call_agent(request: Dict[str, Any],
                           credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.call_agent(**request)
            return result

        @app.post("/mcp/manage_agent")
        async def manage_agent(request: Dict[str, Any],
                             credentials: HTTPAuthorizationCredentials = Depends(app.state.security) if app.state.security else None):
            current_user = await get_authenticated_user(credentials)
            if not app.state.mcp_tools:
                raise HTTPException(status_code=503, detail="MCP tools not available")
            request["user_id"] = current_user.get("sub", current_user.get("id"))
            result = app.state.mcp_tools.manage_agent(**request)
            return result

        logger.info("✅ MCP endpoints registered")

    @staticmethod
    def _add_health_check(app: FastAPI) -> None:
        """Add health check endpoint."""

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            cors_config = cors_factory.get_cors_config()
            return {
                "status": "healthy",
                "service": app.title,
                "version": app.version,
                "authentication": app.state.mcp_auth is not None,
                "mcp_tools": app.state.mcp_tools is not None,
                "cors": cors_config,
            }

        @app.get("/")
        async def root():
            """Root endpoint with API information."""
            return {
                "message": app.title,
                "version": app.version,
                "endpoints": {
                    "/health": "Health check",
                    "/docs": "API documentation",
                    "/api/v2/tokens": "Manage API tokens",
                    "/api/v2/agents": "Agent management",
                    "/api/v2/projects": "Project management",
                    "/api/v2/tasks": "Task management",
                    "/mcp/*": "MCP tool endpoints"
                }
            }


# Singleton instance
app_factory = AppFactory()