"""FastMCP - An ergonomic MCP interface."""

import warnings
from importlib.metadata import version
from typing import TYPE_CHECKING
from fastmcp.settings import Settings

settings = Settings()

# Use lazy loading to avoid circular imports
if TYPE_CHECKING:
    from fastmcp.server.server import FastMCP
    from fastmcp.server.context import Context

# from fastmcp.client import Client
# from . import client

try:
    __version__ = version("agenthub")
except Exception:
    __version__ = "2.0.2.dev"


# ensure deprecation warnings are displayed by default
# if settings.deprecation_warnings:
#     warnings.simplefilter("default", DeprecationWarning)


def __getattr__(name: str):
    """
    Lazy loading for FastMCP classes to avoid circular imports.
    """
    if name == "FastMCP":
        from fastmcp.server.server import FastMCP
        return FastMCP
    elif name == "Context":
        from fastmcp.server.context import Context
        return Context
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# __all__ = [
#     "FastMCP",
#     "Context",
#     "client",
#     "Client",
#     "settings",
# ]

__all__ = ["settings", "FastMCP", "Context"]
