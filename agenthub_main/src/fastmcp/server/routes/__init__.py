"""
Routes module for FastMCP server.
Exposes WebSocket and broadcast routes for real-time communication.
"""

# Import routes modules for easy access
try:
    from . import websocket_routes
    from . import broadcast_routes
    __all__ = ['websocket_routes', 'broadcast_routes']
except ImportError:
    # Routes may not be available in all configurations
    __all__ = []