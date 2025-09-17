from .server import FastMCP
from .context import Context
from . import dependencies

# Import the FastAPI app for ASGI server compatibility
try:
    from .app import app
    __all__ = ["FastMCP", "Context", "app"]
except ImportError:
    # Fallback if app module is not available
    __all__ = ["FastMCP", "Context"]
