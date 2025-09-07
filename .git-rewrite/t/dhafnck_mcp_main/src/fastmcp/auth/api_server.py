#!/usr/bin/env python3
"""
Standalone Authentication API Server

This module provides a FastAPI server for authentication endpoints.
It runs alongside the MCP server to handle auth requests.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import the auth routers
from fastmcp.auth.interface.auth_endpoints import router as auth_router
from fastmcp.auth.api.supabase_endpoints import router as supabase_router
from fastmcp.auth.api.dev_endpoints import router as dev_router

# Import the user-scoped task, project, and context routes
from fastmcp.server.routes.user_scoped_task_routes import router as user_scoped_tasks_router
from fastmcp.server.routes.user_scoped_project_routes import router as user_scoped_projects_router
from fastmcp.server.routes.user_scoped_context_routes import router as user_scoped_contexts_router
from fastmcp.server.routes.token_router import router as token_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DhafnckMCP Authentication API",
    description="Authentication service for DhafnckMCP platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3800", "http://localhost:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routers
app.include_router(auth_router)  # Custom auth endpoints (legacy)
app.include_router(supabase_router)  # Supabase auth endpoints (new)

# Include user-scoped task routes with authentication
app.include_router(user_scoped_tasks_router)  # User-scoped task endpoints at /api/v2/tasks/
logger.info("✅ User-scoped task routes enabled at /api/v2/tasks/")

# Include user-scoped project routes with authentication
app.include_router(user_scoped_projects_router)  # User-scoped project endpoints at /api/v2/projects/
logger.info("✅ User-scoped project routes enabled at /api/v2/projects/")

# Include user-scoped context routes with authentication
app.include_router(user_scoped_contexts_router)  # User-scoped context endpoints at /api/v2/contexts/
logger.info("✅ User-scoped context routes enabled at /api/v2/contexts/")

# Include token management routes with authentication
app.include_router(token_router)  # Token management endpoints at /api/v2/tokens/
logger.info("✅ Token management routes enabled at /api/v2/tokens/")

# Include development endpoints if in dev mode
if os.getenv("ENVIRONMENT", "development") == "development":
    app.include_router(dev_router)  # Development-only endpoints
    logger.warning("⚠️  Development endpoints enabled at /auth/dev/*")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-api"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "DhafnckMCP Authentication API", "version": "1.0.0"}

def main():
    """Run the authentication API server"""
    host = os.getenv("AUTH_API_HOST", "0.0.0.0")
    port = int(os.getenv("AUTH_API_PORT", "8001"))
    
    logger.info(f"Starting Authentication API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()