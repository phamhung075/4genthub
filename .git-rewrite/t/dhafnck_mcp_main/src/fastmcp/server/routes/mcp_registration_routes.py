"""
MCP Registration Routes

Implements the /register endpoint expected by Claude and other MCP clients.
This provides proper MCP protocol registration and session management.
"""

from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import logging
import uuid
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Store active registrations (in production, use Redis or database)
active_registrations: Dict[str, Dict[str, Any]] = {}


async def register_client(request: Request) -> JSONResponse:
    """
    Handle MCP client registration requests.
    
    This endpoint is expected by Claude Desktop and other MCP clients
    to establish a connection with the MCP server.
    """
    
    # Get client information
    client_info = request.client
    user_agent = request.headers.get("user-agent", "Unknown")
    
    try:
        # Parse request body if present
        body = {}
        if request.headers.get("content-type") == "application/json":
            try:
                body = await request.json()
            except:
                pass  # Some clients send empty body
        
        # Generate session ID for this client
        session_id = str(uuid.uuid4())
        
        # Create registration record
        registration = {
            "session_id": session_id,
            "client_ip": client_info.host if client_info else "unknown",
            "client_port": client_info.port if client_info else 0,
            "user_agent": user_agent,
            "registered_at": time.time(),
            "last_activity": time.time(),
            "client_info": body.get("client_info", {}),
            "capabilities": body.get("capabilities", {})
        }
        
        # Store registration
        active_registrations[session_id] = registration
        
        logger.info(f"MCP client registered: {session_id} from {client_info} with User-Agent: {user_agent}")
        
        # Return successful registration response
        response_data = {
            "success": True,
            "session_id": session_id,
            "server": {
                "name": "dhafnck-mcp-server",
                "version": "2.1.0",
                "protocol_version": "2025-06-18"
            },
            "endpoints": {
                "mcp": "http://localhost:8000/mcp/",
                "initialize": "http://localhost:8000/mcp/initialize",
                "tools": "http://localhost:8000/mcp/tools/list",
                "health": "http://localhost:8000/health"
            },
            "transport": "streamable-http",
            "authentication": {
                "required": True,
                "type": "Bearer",
                "header": "Authorization",
                "format": "Bearer YOUR_JWT_TOKEN_HERE"
            },
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "logging": True,
                "progress": True
            },
            "instructions": {
                "next_step": "Initialize connection at /mcp/initialize endpoint",
                "authentication": "Include JWT token in Authorization header",
                "protocol": "Use MCP protocol for all subsequent requests"
            }
        }
        
        # Return successful registration
        return JSONResponse(
            content=response_data,
            status_code=200,
            headers={
                "X-MCP-Server": "dhafnck-mcp-server",
                "X-Session-ID": session_id,
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            }
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return JSONResponse(
            content={
                "error": "Registration failed",
                "message": str(e),
                "instructions": "Please check your client configuration"
            },
            status_code=500,
            headers={
                "X-MCP-Server": "dhafnck-mcp-server",
                "Access-Control-Allow-Origin": "*"
            }
        )


async def unregister_client(request: Request) -> JSONResponse:
    """
    Handle client unregistration/logout.
    """
    try:
        body = await request.json()
        session_id = body.get("session_id")
        
        if session_id and session_id in active_registrations:
            del active_registrations[session_id]
            logger.info(f"MCP client unregistered: {session_id}")
            
            return JSONResponse({
                "success": True,
                "message": "Client unregistered successfully"
            })
        else:
            return JSONResponse(
                content={
                    "error": "Invalid session",
                    "message": "Session ID not found"
                },
                status_code=404
            )
    except Exception as e:
        logger.error(f"Unregistration error: {e}")
        return JSONResponse(
            content={
                "error": "Unregistration failed",
                "message": str(e)
            },
            status_code=500
        )


async def list_registrations(request: Request) -> JSONResponse:
    """
    List active client registrations (for debugging).
    """
    # Clean up old registrations (older than 1 hour)
    current_time = time.time()
    expired_sessions = [
        sid for sid, reg in active_registrations.items()
        if current_time - reg["last_activity"] > 3600
    ]
    for sid in expired_sessions:
        del active_registrations[sid]
    
    return JSONResponse({
        "active_registrations": len(active_registrations),
        "sessions": list(active_registrations.keys()),
        "details": [
            {
                "session_id": sid,
                "client_ip": reg["client_ip"],
                "user_agent": reg["user_agent"],
                "registered_at": reg["registered_at"],
                "last_activity": reg["last_activity"]
            }
            for sid, reg in active_registrations.items()
        ]
    })


async def handle_options(request: Request) -> JSONResponse:
    """
    Handle CORS preflight requests.
    """
    return JSONResponse(
        content={},
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE"
        }
    )


# Define the registration routes
mcp_registration_routes = [
    # Main registration endpoint
    Route("/register", endpoint=register_client, methods=["POST"]),
    Route("/register", endpoint=handle_options, methods=["OPTIONS"]),
    
    # Alternative paths that clients might try
    Route("/api/register", endpoint=register_client, methods=["POST"]),
    Route("/api/register", endpoint=handle_options, methods=["OPTIONS"]),
    Route("/mcp/register", endpoint=register_client, methods=["POST"]),
    Route("/mcp/register", endpoint=handle_options, methods=["OPTIONS"]),
    
    # Unregister endpoint
    Route("/unregister", endpoint=unregister_client, methods=["POST"]),
    Route("/unregister", endpoint=handle_options, methods=["OPTIONS"]),
    
    # Debug endpoint to list registrations
    Route("/registrations", endpoint=list_registrations, methods=["GET"]),
]