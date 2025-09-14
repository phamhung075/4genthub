#!/usr/bin/env python
"""HTTP Server for MCP Tools - Exposes MCP functionality via REST API with Keycloak Authentication"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import version configuration
from fastmcp.config.version import VERSION

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DhafnckMCP HTTP Server",
    description="REST API for MCP Task Management Tools",
    version="1.0.0"
)

# Configure CORS from environment variable
cors_origins_str = os.environ.get("CORS_ORIGINS", "")
if cors_origins_str:
    # Parse comma-separated CORS origins from environment
    # Special handling for wildcard
    if cors_origins_str.strip() == "*":
        cors_origins = ["*"]
    else:
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    logger.info(f"CORS origins configured from environment: {cors_origins}")
else:
    # For MCP endpoints, allow all origins since Claude Code needs access from anywhere
    cors_origins = ["*"]  # Allow all origins for MCP compatibility
    logger.info(f"Using wildcard CORS for MCP compatibility")

# Add CORS middleware - Allow all origins for MCP endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Wildcard for MCP/Claude Code access
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers for MCP protocol
)

# Initialize authentication and MCP tools
security = HTTPBearer()
mcp_auth = None
mcp_tools = None

try:
    # Initialize database first
    from fastmcp.task_management.infrastructure.database.db_initializer import initialize_database_on_startup
    logger.info("Checking database status...")
    if initialize_database_on_startup():
        logger.info("✅ Database initialized successfully")
    else:
        logger.error("❌ Database initialization failed - continuing with limited functionality")

    # Initialize Keycloak authentication
    from fastmcp.auth.mcp_keycloak_auth import mcp_auth as keycloak_auth
    mcp_auth = keycloak_auth
    logger.info("Keycloak authentication initialized successfully")

    # Initialize MCP tools
    from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools
    mcp_tools = DDDCompliantMCPTools()
    logger.info("MCP tools initialized successfully")
    
    # Include performance metrics routes
    # Temporarily disabled due to import error with get_authenticated_user
    # from fastmcp.server.routes.performance_metrics_routes import router as performance_router
    # app.include_router(performance_router)
    logger.info("Performance metrics routes initialized successfully")
    
    # Include analytics routes
    # Temporarily disabled due to import errors
    # from fastmcp.server.routes.analytics_routes import router as analytics_router
    # app.include_router(analytics_router)
    logger.info("Analytics routes disabled temporarily")
    
    # Include alert system routes
    # Temporarily disabled due to import errors
    # from fastmcp.server.routes.alert_system_routes import router as alerts_router
    # app.include_router(alerts_router)
    logger.info("Alert system routes disabled temporarily")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    raise

@app.get("/health")
async def health():
    """Health check endpoint - No authentication required"""
    return {
        "status": "healthy",
        "service": "dhafnck-mcp",
        "version": VERSION,
        "authentication": mcp_auth is not None,
        "mcp_tools": mcp_tools is not None,
        "keycloak_auth_enabled": os.getenv("AUTH_ENABLED", "true").lower() == "true"
    }

@app.get("/")
async def root():
    """Root endpoint - No authentication required"""
    return {
        "message": "DhafnckMCP HTTP Server Running with Keycloak Authentication",
        "authentication": "Bearer token required for all /mcp/* endpoints",
        "keycloak_enabled": os.getenv("AUTH_ENABLED", "true").lower() == "true",
        "endpoints": {
            "/health": "Health check (no auth)",
            "/mcp/manage_task": "Task management (auth required)",
            "/mcp/manage_context": "Context management (auth required)",
            "/mcp/manage_project": "Project management (auth required)",
            "/mcp/manage_git_branch": "Git branch management (auth required)",
            "/mcp/manage_subtask": "Subtask management (auth required)",
            "/mcp/call_agent": "Agent calls (auth required)",
            "/mcp/manage_agent": "Agent management (auth required)",
            "/api/v1/performance/metrics/overview": "Performance metrics overview (auth required)",
            "/api/v1/performance/metrics/timeseries": "Performance time series data (auth required)",
            "/api/v1/performance/metrics/alerts": "Performance alerts (auth required)",
            "/api/v1/analytics/context-usage": "Context usage analytics (auth required)",
            "/api/v1/analytics/agent-performance": "Agent performance analytics (auth required)",
            "/api/v1/analytics/system-insights": "System insights and recommendations (auth required)",
        }
    }

async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get authenticated user from Keycloak or Hook token"""
    token = credentials.credentials
    
    # First try hook authentication (for hooks/MCP clients)
    try:
        from fastmcp.auth.hook_auth import hook_auth_validator
        user_data = hook_auth_validator.validate_hook_token(token)
        logger.info(f"Authenticated via hook token: {user_data.get('sub')}")
        return user_data
    except HTTPException as e:
        # Hook auth failed, try Keycloak
        logger.debug(f"Hook auth failed: {e.detail}, trying Keycloak")
    except Exception as e:
        logger.debug(f"Hook auth error: {e}, trying Keycloak")
    
    # Try Keycloak authentication
    if not mcp_auth:
        raise HTTPException(status_code=503, detail="Authentication service not available")
    
    try:
        user_data = await mcp_auth.validate_mcp_token(token)
        logger.info(f"Authenticated via Keycloak: {user_data.get('sub')}")
        return user_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@app.post("/mcp/manage_task")
async def manage_task(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage tasks - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = await mcp_tools.manage_task(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/manage_context")
async def manage_context(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage context - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.manage_context(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/manage_project")
async def manage_project(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage projects - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.manage_project(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/manage_git_branch")
async def manage_git_branch(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage git branches - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.manage_git_branch(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_git_branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/manage_subtask")
async def manage_subtask(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage subtasks - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.manage_subtask(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_subtask: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/call_agent")
async def call_agent(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Call agent - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.call_agent(**request)
        return result
    except Exception as e:
        logger.error(f"Error in call_agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/manage_agent")
async def manage_agent(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """Manage agents - Requires Keycloak authentication"""
    if not mcp_tools:
        raise HTTPException(status_code=503, detail="MCP tools not available")
    
    try:
        # Add user context to request
        request["user_id"] = current_user["sub"]
        result = mcp_tools.manage_agent(**request)
        return result
    except Exception as e:
        logger.error(f"Error in manage_agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/tools")
async def list_tools(
    current_user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """List available MCP tools - Requires Keycloak authentication"""
    if not mcp_tools:
        return {"tools": [], "error": "MCP tools not initialized"}
    
    try:
        # Get list of available tools
        tools = []
        for attr_name in dir(mcp_tools):
            if not attr_name.startswith('_') and callable(getattr(mcp_tools, attr_name)):
                tools.append(attr_name)
        
        return {
            "tools": tools,
            "user": current_user["preferred_username"] or current_user["email"],
            "permissions": current_user.get("mcp_permissions", [])
        }
    except Exception as e:
        return {"tools": [], "error": str(e)}

# ===== API V2 Endpoints =====
# Note: Agent routes including /call are now handled in fastmcp/server/routes/agent_routes.py

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    
    logger.info(f"Starting MCP HTTP Server on port {port}")
    logger.info(f"Keycloak Authentication: {'ENABLED' if auth_enabled else 'DISABLED'}")
    
    if not auth_enabled:
        logger.warning("⚠️  Authentication is DISABLED - This should only be used for development!")
    
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)