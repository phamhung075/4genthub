"""
MCP Redirect Routes

Handles common MCP client misconfigurations by redirecting to proper endpoints.
This fixes the issue where some Node.js MCP clients try to POST to '/register'
instead of using the proper MCP protocol endpoints.
"""

from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route
from starlette.requests import Request
import logging

logger = logging.getLogger(__name__)


async def register_redirect(request: Request) -> JSONResponse:
    """
    Handle requests to /register endpoint by providing proper MCP connection info.
    
    This endpoint is hit by misconfigured MCP clients that expect a registration
    endpoint instead of using standard MCP protocol initialization.
    """
    
    # Log the client making the request
    client_info = request.client
    user_agent = request.headers.get("user-agent", "Unknown")
    
    logger.info(f"MCP client redirect: {client_info} with User-Agent: {user_agent}")
    logger.info("Client tried to POST to /register - redirecting to proper MCP endpoint")
    
    # Return proper MCP connection information
    response_data = {
        "error": "Invalid endpoint",
        "message": "MCP clients should connect to /mcp/ endpoint, not /register",
        "correct_configuration": {
            "type": "http",
            "url": "http://localhost:8000/mcp/",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
            }
        },
        "protocol": "MCP (Model Context Protocol)",
        "transport": "streamable-http",
        "initialization_endpoint": "/mcp/initialize",
        "documentation": "https://modelcontextprotocol.io/",
        "troubleshooting": {
            "issue": "Client is trying to register instead of following MCP protocol",
            "solution": "Update your MCP client configuration to use the correct endpoint",
            "common_fix": "Check your .mcp.json or claude_desktop_config.json file"
        }
    }
    
    # Return 404 but with helpful information
    return JSONResponse(
        content=response_data,
        status_code=404,
        headers={
            "X-MCP-Server": "dhafnck-mcp-server",
            "X-Proper-Endpoint": "/mcp/",
            "Access-Control-Allow-Origin": "*"
        }
    )


async def health_check(request: Request) -> JSONResponse:
    """Simple health check for load balancers."""
    return JSONResponse({
        "status": "healthy",
        "server": "dhafnck-mcp-server",
        "mcp_endpoint": "/mcp/",
        "auth_required": True
    })


# Define the routes
mcp_redirect_routes = [
    Route("/register", endpoint=register_redirect, methods=["GET", "POST", "OPTIONS"]),
    Route("/api/register", endpoint=register_redirect, methods=["GET", "POST", "OPTIONS"]),
    Route("/health", endpoint=health_check, methods=["GET"]),
]