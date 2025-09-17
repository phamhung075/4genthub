"""
Project MCP Controller - Modular Architecture

This module provides the main project MCP controller with modular architecture.
The controller delegates operations to specialized handlers through factory pattern.
"""

from .project_mcp_controller import ProjectMCPController, description_loader

# Import auth functions for test compatibility
try:
    from ..auth_helper import get_authenticated_user_id, get_current_user_id, validate_user_id
except ImportError:
    get_authenticated_user_id = None
    get_current_user_id = None
    validate_user_id = None

__all__ = ['ProjectMCPController', 'description_loader', 'get_authenticated_user_id', 'get_current_user_id', 'validate_user_id']