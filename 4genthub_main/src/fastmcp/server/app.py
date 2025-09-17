"""
FastMCP Server Application Module

This module exposes the FastAPI app for ASGI servers like uvicorn/gunicorn.
It imports the main MCP HTTP server app for production deployment.
"""

# Import the main FastAPI app from mcp_http_server
import sys
from pathlib import Path

# Add parent directory to path to import mcp_http_server
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the FastAPI app
from mcp_http_server import app

# Expose the app for ASGI servers
__all__ = ["app"]